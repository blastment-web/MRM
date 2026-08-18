<%@ WebHandler Language="C#" Class="Maps" %>
/*  MAPS 등록요청 백엔드 — IIS(ASP.NET) 판
 *
 *  tools/maps_backend.py 와 **같은 계약·같은 파일 형식**을 구현한다. 둘은 서로 바꿔 껴도 된다.
 *  파이썬 판은 실제 화면으로 전 과정을 검증했고(요청→1차→2차→카드 생성→열람, 반려 경로 포함),
 *  이 파일은 그 로직을 1:1 로 옮긴 것이다. Windows·.NET 이 없는 환경에서 만들었기 때문에
 *  **이 파일 자체는 실행 검증을 하지 못했다.**
 *
 *  ── 흐름 ─────────────────────────────────────────────────────────
 *    pending ──1차 승인(admin)──→ it_approved ──2차 승인(다른 관리자)──→ approved → 카드 생성
 *       └──1차 반려──→ rejected            └──2차 반려──→ rejected
 *
 *  ── 저장 위치 ────────────────────────────────────────────────────
 *    C:\inetpub\maps-data\           ← 웹 밖. 여기에 계정·세션·요청·승인 전 파일을 둔다
 *    C:\inetpub\wwwroot\agents\      ← 2차 승인된 것만 여기로 복사된다
 *
 *  계정 파일을 wwwroot 안에 두면 http://IP/data/accounts.json 으로 그대로 읽히고,
 *  승인 전 업로드 파일도 주소만 알면 열린다. 그래서 반드시 밖에 둔다.
 *
 *  주소 형태:  api/maps.ashx?a=<이름>   (화면의 apiFetch 가 이 형태로 재시도한다)
 */

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Web;
using System.Web.Script.Serialization;

public class Maps : IHttpHandler
{
    const int MAX_HTML = 5000000;
    const int SESSION_DAYS = 7;

    /* index.html 의 ORG_ORDER 와 정확히 같아야 한다. 등록 모달 체크박스도 이 4개다. */
    static readonly string[] ORG_ORDER = {
        "新 공정/공법 개발", "해외법인 양산 지원", "제품 개발 대응", "공통 및 루틴 업무"
    };
    const string DEFAULT_COL = "공통 및 루틴 업무";

    HttpContext C;
    string Root;      /* wwwroot           */
    string Data;      /* maps-data (웹 밖) */

    public bool IsReusable { get { return false; } }

    public void ProcessRequest(HttpContext ctx)
    {
        C = ctx;
        C.Response.ContentType = "application/json; charset=utf-8";
        C.Response.AddHeader("Cache-Control", "no-store");

        Root = C.Server.MapPath("~/");
        DirectoryInfo up = Directory.GetParent(Root.TrimEnd('\\', '/'));
        Data = Path.Combine(up != null ? up.FullName : Root, "maps-data");

        try
        {
            Directory.CreateDirectory(Path.Combine(Data, "pending"));
            SeedAccounts();
        }
        catch (Exception) { Fail(500, "데이터 폴더에 쓸 수 없습니다. 1_서버켜기.bat 을 관리자 권한으로 다시 실행하세요."); return; }

        string a = (C.Request.QueryString["a"] ?? "").Trim();
        try
        {
            switch (a)
            {
                case "me":                   Me();            break;
                case "login":                Login();         break;
                case "logout":               Logout();        break;
                case "dash-request":         DashRequest();   break;
                case "dash-requests":        DashRequests();  break;
                case "req-file":             ReqFile();       break;
                case "approve-dash-request": Approve();       break;
                case "dash-request-cancel":  Cancel();        break;
                default: Fail(404, "not implemented"); break;
            }
        }
        catch (Exception) { Fail(500, "서버에서 처리하지 못했습니다."); }
    }

    /* ============================ 엔드포인트 ============================ */

    void Me()
    {
        Dictionary<string, object> s = Session();
        if (s == null) { Write("{\"auth\":false}"); return; }
        Write("{\"auth\":true,\"id\":\"" + Esc(Str(s, "id")) + "\",\"role\":\"" + Esc(Str(s, "role")) + "\"}");
    }

    void Login()
    {
        Dictionary<string, object> b = Body();
        if (b == null) { Fail(400, "요청 형식을 읽지 못했습니다."); return; }
        Dictionary<string, object> u = FindUser(Str(b, "id").Trim());
        if (u == null || Hash(Str(b, "pw"), Str(u, "salt")) != Str(u, "hash"))
        { Fail(401, "아이디 또는 비밀번호가 맞지 않습니다."); return; }

        string sid = NewSession(u);
        C.Response.AddHeader("Set-Cookie", "maps_sid=" + sid + "; Path=/; HttpOnly; SameSite=Lax");
        Write("{\"ok\":true,\"id\":\"" + Esc(Str(u, "id")) + "\",\"role\":\"" + Esc(Str(u, "role")) + "\"}");
    }

    void Logout()
    {
        Dictionary<string, object> ss = ReadObj(Path.Combine(Data, "sessions.json"));
        string sid = Sid();
        if (ss.ContainsKey(sid)) { ss.Remove(sid); WriteObj(Path.Combine(Data, "sessions.json"), ss, false); }
        C.Response.AddHeader("Set-Cookie", "maps_sid=; Path=/; Max-Age=0");
        Write("{\"ok\":true}");
    }

    void DashRequest()
    {
        Dictionary<string, object> b = Body();
        if (b == null) { Fail(400, "요청 형식을 읽지 못했습니다."); return; }
        string name = Str(b, "name").Trim();
        string html = Str(b, "html");
        if (name.Length == 0) { Fail(400, "AI Agent 명이 필요합니다."); return; }
        if (html.Length > MAX_HTML) { Fail(413, "파일이 너무 큽니다."); return; }

        Dictionary<string, object> db = ReadObj(Path.Combine(Data, "requests.json"));
        List<object> items = AsList(db.ContainsKey("items") ? db["items"] : null);

        string stamp = DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        string bas = Slug(name);
        if (bas.Length == 0) bas = Slug(Path.GetFileNameWithoutExtension(Str(b, "fname")));
        string rid = bas.Length > 0 ? stamp + "-" + bas : stamp;
        /* 같은 초에 두 건이 들어와도 겹치지 않게 한다 */
        HashSet<string> used = new HashSet<string>(items.Select(x => Str(AsObj(x), "id")));
        if (used.Contains(rid))
        {
            int n = 2;
            while (used.Contains(rid + "-" + n)) n++;
            rid = rid + "-" + n;
        }

        if (html.Length > 0)
            File.WriteAllText(Path.Combine(Path.Combine(Data, "pending"), rid + ".html"),
                              html, new UTF8Encoding(false));

        string org = Str(b, "org").Trim(), team = Str(b, "team").Trim();
        Dictionary<string, object> it = new Dictionary<string, object>();
        it["id"] = rid;
        it["name"] = name;
        it["desc"] = Str(b, "desc").Trim();
        it["org"] = org;
        it["team"] = team;
        it["features"] = b.ContainsKey("features") ? b["features"] : new object[0];
        it["etc"] = Str(b, "etc").Trim();
        it["fname"] = Str(b, "fname").Trim();
        it["file"] = html.Length > 0;
        it["bytes"] = html.Length;
        it["ts"] = Now();
        it["status"] = "pending";
        it["requester"] = Str(b, "author").Trim().Length > 0 ? Str(b, "author").Trim() : "(익명)";
        it["requesterName"] = Str(b, "author").Trim();
        it["requesterOrg"] = (org + " " + team).Trim();
        it["stage1"] = null;
        it["stage2"] = null;

        items.Insert(0, it);
        db["items"] = items;
        WriteObj(Path.Combine(Data, "requests.json"), db, false);
        Write("{\"ok\":true,\"id\":\"" + Esc(rid) + "\"}");
    }

    void DashRequests()
    {
        if (Session() == null) { Fail(401, "로그인이 필요합니다."); return; }
        Dictionary<string, object> db = ReadObj(Path.Combine(Data, "requests.json"));
        List<object> items = AsList(db.ContainsKey("items") ? db["items"] : null);
        Dictionary<string, object> res = new Dictionary<string, object>();
        res["ok"] = true; res["items"] = items;
        Write(new JavaScriptSerializer().Serialize(res));
    }

    void ReqFile()
    {
        if (Session() == null) { Fail(401, "로그인이 필요합니다."); return; }
        string id = SafeId(C.Request.QueryString["id"]);
        string p = Path.Combine(Path.Combine(Data, "pending"), id + ".html");
        if (id.Length == 0 || !File.Exists(p)) { Fail(404, "파일이 없습니다."); return; }
        C.Response.ContentType = "text/html; charset=utf-8";
        C.Response.AddHeader("Content-Disposition", "attachment; filename=\"" + id + ".html\"");
        C.Response.BinaryWrite(File.ReadAllBytes(p));
    }

    void Approve()
    {
        Dictionary<string, object> me = Session();
        if (me == null || Str(me, "role") != "admin") { Fail(403, "관리자만 처리할 수 있습니다."); return; }
        Dictionary<string, object> b = Body();
        if (b == null) { Fail(400, "요청 형식을 읽지 못했습니다."); return; }

        string rid = Str(b, "id");
        bool approve = b.ContainsKey("approve") && Convert.ToBoolean(b["approve"]);
        string reason = Str(b, "reason").Trim();

        Dictionary<string, object> db = ReadObj(Path.Combine(Data, "requests.json"));
        List<object> items = AsList(db.ContainsKey("items") ? db["items"] : null);
        Dictionary<string, object> req = null;
        foreach (object o in items) { if (Str(AsObj(o), "id") == rid) { req = AsObj(o); break; } }
        if (req == null) { Fail(404, "요청을 찾을 수 없습니다."); return; }

        bool isSuper = Str(me, "id") == "admin";
        Dictionary<string, object> stamp = new Dictionary<string, object>();
        stamp["by"] = Str(me, "id");
        stamp["ts"] = Now();
        stamp["decision"] = approve ? "approved" : "rejected";
        stamp["reason"] = reason;

        string st = Str(req, "status");
        if (st == "pending")
        {
            if (!isSuper) { Fail(403, "1차 검토는 admin 계정만 할 수 있습니다."); return; }
            if (!approve && reason.Length == 0) { Fail(400, "반려 사유가 필요합니다."); return; }
            req["stage1"] = stamp;
            req["status"] = approve ? "it_approved" : "rejected";
        }
        else if (st == "it_approved")
        {
            if (isSuper) { Fail(403, "2차 검토는 다른 관리자 계정이 해야 합니다."); return; }
            if (!approve && reason.Length == 0) { Fail(400, "반려 사유가 필요합니다."); return; }
            req["stage2"] = stamp;
            req["status"] = approve ? "approved" : "rejected";
            if (approve) req["addr"] = Publish(req);
        }
        else { Fail(400, "이미 처리된 요청입니다."); return; }

        db["items"] = items;
        WriteObj(Path.Combine(Data, "requests.json"), db, false);
        Write("{\"ok\":true,\"status\":\"" + Esc(Str(req, "status")) + "\"}");
    }

    void Cancel()
    {
        Dictionary<string, object> me = Session();
        if (me == null || Str(me, "role") != "admin") { Fail(403, "관리자만 처리할 수 있습니다."); return; }
        Dictionary<string, object> b = Body();
        string rid = b == null ? "" : Str(b, "id");
        Dictionary<string, object> db = ReadObj(Path.Combine(Data, "requests.json"));
        List<object> items = AsList(db.ContainsKey("items") ? db["items"] : null);
        int before = items.Count;
        items = items.Where(x => Str(AsObj(x), "id") != rid).ToList();
        db["items"] = items;
        WriteObj(Path.Combine(Data, "requests.json"), db, false);
        Write("{\"ok\":true,\"removed\":" + (before - items.Count) + "}");
    }

    /* ============================ 카드 생성 ============================ */

    string Publish(Dictionary<string, object> req)
    {
        string slug = Str(req, "id");
        string src = Path.Combine(Path.Combine(Data, "pending"), slug + ".html");
        if (File.Exists(src))
        {
            string dir = Path.Combine(Path.Combine(Root, "agents"), slug);
            Directory.CreateDirectory(dir);
            File.Copy(src, Path.Combine(dir, "index.html"), true);
        }

        string host = C.Request.Headers["Host"];
        if (string.IsNullOrEmpty(host)) host = "localhost";
        string addr = "http://" + host + "/agents/" + slug + "/";

        /* 카테고리 비교는 공백을 무시한다 — "新 공정/공법 개발" 과 "新공정/공법 개발" 처럼
           띄어쓰기 하나로 엉뚱한 칸에 들어가면 원인을 찾기 어렵다. */
        string team = DEFAULT_COL;
        foreach (object f in AsList(req.ContainsKey("features") ? req["features"] : null))
        {
            string fs = Norm(Convert.ToString(f));
            foreach (string o in ORG_ORDER) if (Norm(o) == fs) { team = o; break; }
            if (team != DEFAULT_COL) break;
        }

        foreach (string path in DashboardFiles())
        {
            Dictionary<string, object> data = ReadObj(path);
            if (!data.ContainsKey("columns")) continue;
            List<object> cols = AsList(data["columns"]);
            Dictionary<string, object> col = null;
            foreach (object c in cols)
                if (Norm(Str(AsObj(c), "team")) == Norm(team)) { col = AsObj(c); break; }
            if (col == null)
                foreach (object c in cols)
                    if (Norm(Str(AsObj(c), "team")).StartsWith(Norm(team))) { col = AsObj(c); break; }
            if (col == null) continue;

            List<object> items = AsList(col.ContainsKey("items") ? col["items"] : null);
            bool dup = false;
            foreach (object o in items) if (Str(AsObj(o), "addr") == addr) { dup = true; break; }
            if (dup) continue;

            /* 맨 앞에 놓는다. 뒤에 붙이면 기본 표시 개수(3개) 밖으로 밀려
               "승인했는데 카드가 안 보인다" 가 된다. 목록은 order 오름차순이다. */
            int minOrder = 1;
            foreach (object o in items)
            {
                int v = ToInt(AsObj(o).ContainsKey("order") ? AsObj(o)["order"] : null);
                if (v < minOrder) minOrder = v;
            }

            Dictionary<string, object> card = new Dictionary<string, object>();
            card["name"] = Str(req, "name");
            card["desc"] = Str(req, "desc");
            card["owner"] = Str(req, "requesterName");
            card["addr"] = addr;
            card["order"] = minOrder - 1;
            card["org"] = Str(req, "org");
            card["likes"] = 0;
            card["linkedAt"] = DateTime.Now.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            items.Add(card);
            col["items"] = items;
            data["columns"] = cols;
            WriteObj(path, data, true);
        }
        return addr;
    }

    List<string> DashboardFiles()
    {
        /* 화면 폴더마다 사본이 있다. 전부 찾아 같이 고친다. */
        List<string> outp = new List<string>();
        string r = Path.Combine(Path.Combine(Root, "data"), "dashboards.json");
        if (File.Exists(r)) outp.Add(r);
        foreach (string d in Directory.GetDirectories(Root))
        {
            string q = Path.Combine(Path.Combine(d, "data"), "dashboards.json");
            if (File.Exists(q)) outp.Add(q);
        }
        return outp;
    }

    /* ============================ 계정·세션 ============================ */

    void SeedAccounts()
    {
        string p = Path.Combine(Data, "accounts.json");
        if (File.Exists(p)) return;
        List<object> users = new List<object>();
        foreach (string uid in new string[] { "admin", "manager" })
        {
            string salt = Guid.NewGuid().ToString("N").Substring(0, 16);
            Dictionary<string, object> u = new Dictionary<string, object>();
            u["id"] = uid; u["role"] = "admin"; u["salt"] = salt; u["hash"] = Hash("maps2026!", salt);
            users.Add(u);
        }
        Dictionary<string, object> o = new Dictionary<string, object>();
        o["users"] = users;
        WriteObj(p, o, false);
    }

    Dictionary<string, object> FindUser(string id)
    {
        foreach (object o in AsList(ReadObj(Path.Combine(Data, "accounts.json")).ContainsKey("users")
                 ? ReadObj(Path.Combine(Data, "accounts.json"))["users"] : null))
            if (Str(AsObj(o), "id") == id) return AsObj(o);
        return null;
    }

    string NewSession(Dictionary<string, object> u)
    {
        string path = Path.Combine(Data, "sessions.json");
        Dictionary<string, object> ss = ReadObj(path);
        string sid = Guid.NewGuid().ToString("N") + Guid.NewGuid().ToString("N").Substring(0, 8);
        Dictionary<string, object> s = new Dictionary<string, object>();
        s["id"] = Str(u, "id"); s["role"] = Str(u, "role");
        s["exp"] = DateTime.Now.AddDays(SESSION_DAYS).ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        ss[sid] = s;
        WriteObj(path, ss, false);
        return sid;
    }

    string Sid()
    {
        HttpCookie c = C.Request.Cookies["maps_sid"];
        return c == null ? "" : (c.Value ?? "");
    }

    Dictionary<string, object> Session()
    {
        string sid = Sid();
        if (sid.Length == 0) return null;
        Dictionary<string, object> ss = ReadObj(Path.Combine(Data, "sessions.json"));
        if (!ss.ContainsKey(sid)) return null;
        Dictionary<string, object> s = AsObj(ss[sid]);
        DateTime exp;
        if (!DateTime.TryParseExact(Str(s, "exp"), "yyyy-MM-dd HH:mm:ss",
             CultureInfo.InvariantCulture, DateTimeStyles.None, out exp)) return null;
        return exp < DateTime.Now ? null : s;
    }

    /* ============================ 도우미 ============================ */

    static string Now() { return DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture); }

    static string Norm(string s)
    {
        if (s == null) return "";
        StringBuilder sb = new StringBuilder();
        foreach (char c in s) if (!char.IsWhiteSpace(c)) sb.Append(c);
        return sb.ToString();
    }

    static string Hash(string pw, string salt)
    {
        using (SHA256 sha = SHA256.Create())
        {
            byte[] h = sha.ComputeHash(Encoding.UTF8.GetBytes(salt + "|" + pw));
            StringBuilder sb = new StringBuilder();
            foreach (byte x in h) sb.Append(x.ToString("x2"));
            return sb.ToString();
        }
    }

    /* 영문 소문자·숫자·하이픈만 남긴다. `../` 나 한글이 들어와도 폴더 밖으로 못 나간다. */
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

    /* 요청 id 는 우리가 만든 값이지만, 밖에서 들어온 것으로 취급해 한 번 더 거른다. */
    static string SafeId(string s)
    {
        if (string.IsNullOrEmpty(s)) return "";
        StringBuilder sb = new StringBuilder();
        foreach (char c in s)
            if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '-')
                sb.Append(c);
        return sb.ToString().Length > 60 ? sb.ToString().Substring(0, 60) : sb.ToString();
    }

    Dictionary<string, object> Body()
    {
        try
        {
            C.Request.InputStream.Position = 0;
            using (StreamReader sr = new StreamReader(C.Request.InputStream, Encoding.UTF8))
            {
                string raw = sr.ReadToEnd();
                if (raw.Length == 0) return new Dictionary<string, object>();
                JavaScriptSerializer js = new JavaScriptSerializer();
                js.MaxJsonLength = int.MaxValue;
                return js.Deserialize<Dictionary<string, object>>(raw);
            }
        }
        catch (Exception) { return null; }
    }

    static Dictionary<string, object> AsObj(object o)
    {
        return o as Dictionary<string, object> ?? new Dictionary<string, object>();
    }

    static List<object> AsList(object o)
    {
        if (o == null) return new List<object>();
        List<object> l = o as List<object>;
        if (l != null) return l;
        object[] a = o as object[];
        if (a != null) return new List<object>(a);
        IEnumerable e = o as IEnumerable;
        if (e != null && !(o is string)) { List<object> r = new List<object>(); foreach (object x in e) r.Add(x); return r; }
        return new List<object>();
    }

    static string Str(Dictionary<string, object> o, string k)
    {
        if (o == null || !o.ContainsKey(k) || o[k] == null) return "";
        return Convert.ToString(o[k]);
    }

    static int ToInt(object o)
    {
        if (o == null) return 0;
        int v;
        return int.TryParse(Convert.ToString(o), out v) ? v : 0;
    }

    Dictionary<string, object> ReadObj(string path)
    {
        try
        {
            if (!File.Exists(path)) return new Dictionary<string, object>();
            JavaScriptSerializer js = new JavaScriptSerializer();
            js.MaxJsonLength = int.MaxValue;
            return js.Deserialize<Dictionary<string, object>>(File.ReadAllText(path, Encoding.UTF8))
                   ?? new Dictionary<string, object>();
        }
        catch (Exception) { return new Dictionary<string, object>(); }
    }

    /* 임시 파일에 쓰고 이름을 바꾼다. 쓰는 도중에 죽어도 원본이 반쯤 망가지지 않는다. */
    void WriteObj(string path, object obj, bool backup)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        if (backup && File.Exists(path)) File.Copy(path, path + ".bak", true);
        string tmp = path + ".tmp";
        JavaScriptSerializer js = new JavaScriptSerializer();
        js.MaxJsonLength = int.MaxValue;
        File.WriteAllText(tmp, js.Serialize(obj), new UTF8Encoding(false));
        if (File.Exists(path)) File.Delete(path);
        File.Move(tmp, path);
    }

    void Write(string json)
    {
        C.Response.StatusCode = 200;
        C.Response.Write(json);
    }

    void Fail(int code, string msg)
    {
        C.Response.StatusCode = code;
        C.Response.Write("{\"ok\":false,\"error\":\"" + Esc(msg) + "\"}");
    }

    static string Esc(string s)
    {
        if (s == null) return "";
        return s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", " ").Replace("\n", " ");
    }
}
