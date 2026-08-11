<%@ WebHandler Language="C#" Class="DashRequest" %>
/*  MAPS — AI Agent 등록요청 받기
 *
 *  화면(＋ AI Agent 등록)이 보내는 JSON 을 받아 HTML 을 서버에 저장한다.
 *  .NET Framework 4.x 는 Windows 에 이미 들어 있고, IIS 의 ASP.NET 기능만 켜면
 *  이 파일 하나로 동작한다. 새로 내려받을 것도, web.config 도 필요 없다.
 *
 *  ── 설계 원칙 두 가지 ──────────────────────────────────────────────
 *
 *  1) 하는 일을 최소로 둔다. 저장 외에는 아무것도 하지 않는다.
 *
 *  2) **업로드와 공개를 분리한다.** dashboards.json 을 절대 건드리지 않는다.
 *     올라간 파일은 관리자가 dashboards.json 의 addr 을 채우기 전까지 카드에
 *     나타나지 않는다(앱의 isLive() 규칙). 즉 아무나 올릴 수는 있어도
 *     아무나 게시할 수는 없다. 서버 코드가 카드 목록을 고치면 그 파일이 깨졌을 때
 *     화면 전체가 영향을 받는다 — 그래서 손대지 않는다.
 *
 *  저장 위치는 코드가 정하고 요청 값은 폴더 "이름" 에만 쓰인다. 그 이름도
 *  [a-z0-9-] 로만 정제하므로 요청이 경로를 벗어날 수 없다.
 */

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web;
using System.Web.Script.Serialization;

public class DashRequest : IHttpHandler
{
    const int MAX_HTML = 5000000;      /* 글자 수. 화면 쪽에서 3MB 로 한 번 더 막는다 */

    public bool IsReusable { get { return false; } }

    public void ProcessRequest(HttpContext ctx)
    {
        ctx.Response.ContentType = "application/json; charset=utf-8";
        ctx.Response.AddHeader("Cache-Control", "no-store");

        /* 브라우저로 그냥 열면 상태를 알려 준다 — ASP.NET 이 켜졌는지 확인하는 용도 */
        if (ctx.Request.HttpMethod == "GET") { Status(ctx); return; }
        if (ctx.Request.HttpMethod != "POST") { Fail(ctx, 405, "POST 로만 받습니다."); return; }

        string body;
        try
        {
            ctx.Request.InputStream.Position = 0;
            using (StreamReader sr = new StreamReader(ctx.Request.InputStream, Encoding.UTF8))
                body = sr.ReadToEnd();
        }
        catch (Exception) { Fail(ctx, 400, "요청 본문을 읽지 못했습니다."); return; }

        if (string.IsNullOrEmpty(body)) { Fail(ctx, 400, "요청 본문이 비어 있습니다."); return; }

        Dictionary<string, object> o = null;
        try
        {
            JavaScriptSerializer js = new JavaScriptSerializer();
            js.MaxJsonLength = int.MaxValue;
            o = js.Deserialize<Dictionary<string, object>>(body);
        }
        catch (Exception) { }
        if (o == null) { Fail(ctx, 400, "요청 형식을 읽지 못했습니다."); return; }

        string name  = Str(o, "name");
        string html  = Str(o, "html");
        string fname = Str(o, "fname");

        if (name.Length == 0) { Fail(ctx, 400, "AI Agent 명이 필요합니다."); return; }
        if (html.Length > MAX_HTML) { Fail(ctx, 413, "파일이 너무 큽니다."); return; }

        /* 시각을 앞에 붙여 같은 이름이 겹쳐도 덮어쓰지 않게 한다.
           두 사람이 같은 이름으로 올렸을 때 먼저 것이 사라지는 사고를 막는다. */
        string stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        string baseName = Slug(name);
        if (baseName.Length == 0) baseName = Slug(StripExt(fname));
        string slug = baseName.Length > 0 ? stamp + "-" + baseName : stamp;

        try
        {
            string root = ctx.Server.MapPath("~/");          /* 사이트 루트 = wwwroot */
            string reqDir = Path.Combine(root, "requests");
            Directory.CreateDirectory(reqDir);

            if (html.Length > 0)
            {
                string dir = Path.Combine(Path.Combine(root, "agents"), slug);
                Directory.CreateDirectory(dir);
                File.WriteAllText(Path.Combine(dir, "index.html"), html, new UTF8Encoding(false));
            }

            Dictionary<string, object> meta = new Dictionary<string, object>();
            meta["slug"]     = slug;
            meta["name"]     = name;
            meta["author"]   = Str(o, "author");
            meta["org"]      = Str(o, "org");
            meta["team"]     = Str(o, "team");
            meta["desc"]     = Str(o, "desc");
            meta["etc"]      = Str(o, "etc");
            meta["features"] = o.ContainsKey("features") ? o["features"] : null;
            meta["fname"]    = fname;
            meta["hasFile"]  = html.Length > 0;
            meta["bytes"]    = html.Length;
            meta["at"]       = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
            meta["from"]     = ctx.Request.UserHostAddress;

            File.WriteAllText(Path.Combine(reqDir, slug + ".json"),
                              new JavaScriptSerializer().Serialize(meta), new UTF8Encoding(false));

            /* 관리자가 명령창에서 바로 읽을 수 있게 CP949 요약도 함께 남긴다.
               UTF-8 JSON 을 한국어 Windows 콘솔에서 type 하면 한글이 깨진다. */
            StringBuilder txt = new StringBuilder();
            txt.AppendLine("  AI Agent 명 : " + name);
            txt.AppendLine("  요청자      : " + Str(o, "author") + "  /  " + Str(o, "org") + "  " + Str(o, "team"));
            txt.AppendLine("  설명        : " + Str(o, "desc"));
            txt.AppendLine("  원본 파일   : " + (fname.Length > 0 ? fname : "(첨부 없음)")
                                              + (html.Length > 0 ? "  (" + html.Length + "자)" : ""));
            txt.AppendLine("  받은 시각   : " + meta["at"] + "   from " + ctx.Request.UserHostAddress);
            File.WriteAllText(Path.Combine(reqDir, slug + ".txt"), txt.ToString(),
                              Encoding.GetEncoding(949));
        }
        catch (UnauthorizedAccessException)
        {
            Fail(ctx, 500, "서버 폴더에 쓸 권한이 없습니다. 관리자에게 1_서버켜기.bat 재실행을 요청하세요.");
            return;
        }
        catch (Exception) { Fail(ctx, 500, "서버에 저장하지 못했습니다."); return; }

        ctx.Response.StatusCode = 200;
        ctx.Response.Write("{\"ok\":true,\"slug\":\"" + Esc(slug) + "\"}");
    }

    /* ---- 도우미 ---------------------------------------------------- */

    static void Status(HttpContext ctx)
    {
        bool writable = false;
        string where = "";
        try
        {
            where = Path.Combine(ctx.Server.MapPath("~/"), "requests");
            Directory.CreateDirectory(where);
            string probe = Path.Combine(where, ".write-test");
            File.WriteAllText(probe, "ok");
            File.Delete(probe);
            writable = true;
        }
        catch (Exception) { }
        ctx.Response.StatusCode = 200;
        ctx.Response.Write("{\"ok\":true,\"ready\":true,\"writable\":" + (writable ? "true" : "false")
                           + ",\"path\":\"" + Esc(where) + "\"}");
    }

    static void Fail(HttpContext ctx, int code, string msg)
    {
        ctx.Response.StatusCode = code;
        ctx.Response.Write("{\"ok\":false,\"error\":\"" + Esc(msg) + "\"}");
    }

    static string Str(Dictionary<string, object> o, string k)
    {
        if (o == null || !o.ContainsKey(k) || o[k] == null) return "";
        return Convert.ToString(o[k]);
    }

    static string StripExt(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        int i = s.LastIndexOf('.');
        return i > 0 ? s.Substring(0, i) : s;
    }

    /* 영문 소문자·숫자·하이픈만 남긴다. 한글·공백·경로 기호는 전부 사라지므로
       "../" 같은 값이 들어와도 폴더 이름 밖으로 나갈 수 없다. */
    static string Slug(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        StringBuilder sb = new StringBuilder();
        foreach (char c in s.ToLowerInvariant())
        {
            if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) sb.Append(c);
            else if (c == '-' || c == '_' || c == ' ' || c == '.') sb.Append('-');
        }
        string t = sb.ToString();
        while (t.Contains("--")) t = t.Replace("--", "-");
        t = t.Trim('-');
        if (t.Length > 40) t = t.Substring(0, 40).Trim('-');
        return t;
    }

    static string Esc(string s)
    {
        if (s == null) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", " ").Replace("\n", " ");
    }
}
