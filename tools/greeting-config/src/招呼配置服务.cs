using System;
using System.IO;
using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using System.Threading;
using System.Diagnostics;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using System.Xml;

// Windows 自带 .NET Framework；界面内嵌到 EXE；数据目录始终取本程序所在目录。
internal static class GreetingConfig {
    const string EmbeddedAiKey = "";
    static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 16000000, RecursionLimit = 64 };
    static string Root, RootHash, Token, Origin, BaseUrl;
    static bool Running = true, NoBrowser;
    static DateTime LastActivity = DateTime.UtcNow;
    static readonly string BackupDir = ".招呼配置备份";
    static string StatePath, LocalDir;
    static List<Dictionary<string, object>> AreaIndexCache;
    static readonly Dictionary<int, List<Dictionary<string, object>>> AreaBoundaryCache = new Dictionary<int, List<Dictionary<string, object>>>();

    [STAThread]
    static void Main(string[] args) {
        ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
        Root = Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
        RootHash = Hash(Utf8.GetBytes(Root.ToUpperInvariant())).Substring(0, 24);
        foreach (string a in args) if (a == "--no-browser") NoBrowser = true;
        bool created;
        using (Mutex mutex = new Mutex(true, "Local\\GreetingConfig-Embedded-" + RootHash, out created)) {
            string stateDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "GreetingConfig");
            Directory.CreateDirectory(stateDir);
            LocalDir = stateDir;
            StatePath = Path.Combine(stateDir, "embedded-" + RootHash + ".json");
            if (!created) {
                for (int i = 0; i < 30; i++) {
                    try {
                        Dictionary<string, object> state = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(StatePath, Utf8));
                        string url = Str(state, "url");
                        Uri uri = new Uri(url);
                        if (uri.Scheme != "http" || uri.Host != "127.0.0.1" || !Regex.IsMatch(uri.AbsolutePath, "^/[a-f0-9]{64}/$")) throw new Exception("无效的本地地址。");
                        using (WebClient client = new WebClient()) {
                            if (client.DownloadString(url + "health") != RootHash) throw new Exception("旧的启动状态。");
                        }
                        if (!NoBrowser) Process.Start(url);
                        return;
                    } catch { Thread.Sleep(100); }
                }
                if (!NoBrowser) MessageBox.Show("配置面板正在启动，请稍后再双击一次。", "招呼配置");
                return;
            }
            TcpListener listener = null;
            try {
                if (String.IsNullOrEmpty(LoadPage())) throw new Exception("程序内嵌界面缺失，请重新获取完整的 EXE。");
                Token = RandomId(32);
                listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start(8);
                Origin = "http://127.0.0.1:" + ((IPEndPoint)listener.LocalEndpoint).Port;
                BaseUrl = Origin + "/" + Token + "/";
                File.WriteAllText(StatePath, Json.Serialize(new { url = BaseUrl, pid = Process.GetCurrentProcess().Id, root = Root }), Utf8);
                if (!NoBrowser) Process.Start(BaseUrl);
                while (Running && DateTime.UtcNow - LastActivity < TimeSpan.FromMinutes(1)) {
                    if (!listener.Pending()) { Thread.Sleep(60); continue; }
                    using (TcpClient client = listener.AcceptTcpClient()) {
                        client.ReceiveTimeout = 12000; client.SendTimeout = 12000;
                        try { Handle(client.GetStream()); } catch { }
                    }
                }
            } catch (Exception e) {
                if (!NoBrowser) MessageBox.Show(e.Message, "招呼配置启动失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            } finally {
                if (listener != null) listener.Stop();
                try { File.Delete(StatePath); } catch { }
                mutex.ReleaseMutex();
            }
        }
    }

    static string LoadPage() {
        using (Stream resource = typeof(GreetingConfig).Assembly.GetManifestResourceStream("GreetingConfig.Html")) {
            if (resource == null) throw new Exception("程序内嵌界面资源不存在。");
            using (StreamReader reader = new StreamReader(resource, Utf8, true)) return reader.ReadToEnd();
        }
    }

    static void Handle(NetworkStream stream) {
        try {
            List<byte> head = new List<byte>();
            while (head.Count < 16384) {
                int b = stream.ReadByte(); if (b < 0) return; head.Add((byte)b);
                int n = head.Count;
                if (n >= 4 && head[n-4] == 13 && head[n-3] == 10 && head[n-2] == 13 && head[n-1] == 10) break;
            }
            if (head.Count >= 16384) throw new Exception("请求头过长。");
            string[] headers = Encoding.ASCII.GetString(head.ToArray()).Split(new string[] { "\r\n" }, StringSplitOptions.None);
            string[] request = headers[0].Split(' ');
            if (request.Length != 3) throw new Exception("请求格式无效。");
            Dictionary<string, string> h = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (int i = 1; i < headers.Length; i++) { int p = headers[i].IndexOf(':'); if (p > 0) h[headers[i].Substring(0, p)] = headers[i].Substring(p+1).Trim(); }
            string expectedHost = Origin.Substring("http://".Length);
            if (!h.ContainsKey("Host") || h["Host"] != expectedHost || (h.ContainsKey("Origin") && h["Origin"] != Origin)) { Reply(stream, 403, "text/plain", Utf8.GetBytes("拒绝访问。")); return; }
            string route = request[1];
            string prefix = "/" + Token + "/";
            if (!route.StartsWith(prefix, StringComparison.Ordinal)) { Reply(stream, 404, "text/plain", new byte[0]); return; }
            route = route.Substring(prefix.Length);
            LastActivity = DateTime.UtcNow;
            if (request[0] == "GET" && route == "health") { Reply(stream, 200, "text/plain", Utf8.GetBytes(RootHash)); return; }
            if (request[0] == "GET" && (route == "" || route == "招呼配置.html")) {
                string html = LoadPage();
                string boot = Json.Serialize(new { rootName = new DirectoryInfo(Root).Name, root = Root, api = BaseUrl + "api", token = Token }).Replace("<", "\\u003c");
                html = html.Replace("<!--LOCAL_BOOT-->", "<script>window.__CONFIG_SESSION__=" + boot + ";</script>");
                Reply(stream, 200, "text/html", Utf8.GetBytes(html)); return;
            }
            if (route != "api" || request[0] != "POST" || !h.ContainsKey("X-Config-Token") || h["X-Config-Token"] != Token) { Reply(stream, 403, "text/plain", new byte[0]); return; }
            if (h.ContainsKey("Transfer-Encoding")) throw new Exception("不支持此传输格式。");
            int length;
            if (!h.ContainsKey("Content-Length") || !int.TryParse(h["Content-Length"], out length) || length < 0 || length > 12000000) throw new Exception("请求内容过大或无效。");
            byte[] body = new byte[length]; int offset = 0;
            while (offset < length) { int n = stream.Read(body, offset, length-offset); if (n == 0) throw new Exception("请求中断。"); offset += n; }
            Dictionary<string, object> input = Json.Deserialize<Dictionary<string, object>>(Utf8.GetString(body));
            object result = Action(input);
            Reply(stream, 200, "application/json", Utf8.GetBytes(Json.Serialize(new { ok = true, data = result })));
        } catch (Exception e) {
            Reply(stream, 400, "application/json", Utf8.GetBytes(Json.Serialize(new { ok = false, error = e.Message })));
        }
    }

    static void Reply(NetworkStream stream, int status, string mime, byte[] body) {
        string headers = "HTTP/1.1 " + status + (status == 200 ? " OK" : " Error") + "\r\nContent-Type: " + mime + "; charset=utf-8\r\nContent-Length: " + body.Length + "\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nReferrer-Policy: no-referrer\r\nCross-Origin-Resource-Policy: same-origin\r\n\r\n";
        byte[] bytes = Encoding.ASCII.GetBytes(headers); stream.Write(bytes, 0, bytes.Length); stream.Write(body, 0, body.Length); stream.Flush();
    }

    static object Action(Dictionary<string, object> a) {
        string action = Str(a, "action");
        if (action == "ping") return new { alive = true };
        if (action == "stop") { Running = false; return new { stopped = true }; }
        if (action == "syncthing-status") return SyncthingStatus(false);
        if (action == "syncthing-toggle") return SyncthingStatus(true);
        if (action == "favorites-list") return new { paths = LoadFavorites() };
        if (action == "favorite-toggle") return ToggleFavorite(Str(a, "path"));
        if (action == "ai-key-status") return new { configured = File.Exists(SecretPath()) };
        if (action == "ai-key-set") { SetAiKey(Str(a, "key")); return new { configured = true }; }
        if (action == "ai-expand") return AiExpand(a);
        if (action == "list") {
            List<object> files = new List<object>(); List<string> directories = new List<string>();
            Scan(Root, files, directories);
            return new { files = files, directories = directories, rootName = new DirectoryInfo(Root).Name, root = Root };
        }
        if (action == "history") {
            List<object> list = new List<object>();
            string bdir = Safe(BackupDir, true);
            if (Directory.Exists(bdir)) ScanHistory(bdir, list);
            return list;
        }
        if (action == "read") return Read(SafeMd(Str(a, "path")));
        if (action == "save") {
            string full = SafeMd(Str(a, "path")); byte[] old = Expected(full, Str(a, "version"));
            byte[] next = Encode(Str(a, "text"), HasBom(old));
            if (Hash(next) != Hash(old)) { Backup(full, "保存前"); AtomicWrite(full, next); }
            return Read(full);
        }
        if (action == "create") {
            string full = SafeMd(Str(a, "path"));
            if (File.Exists(full) || Directory.Exists(full)) throw new Exception("已有同名文件，请换一个名称。");
            Directory.CreateDirectory(Path.GetDirectoryName(full));
            byte[] data = Encode(Str(a, "text"), false);
            using (FileStream stream = new FileStream(full, FileMode.CreateNew, FileAccess.Write, FileShare.None)) stream.Write(data, 0, data.Length);
            return Read(full);
        }
        if (action == "rename") {
            string full = SafeMd(Str(a, "path")), target = SafeMd(Str(a, "target"));
            Expected(full, Str(a, "version"));
            if (full.Equals(target, StringComparison.OrdinalIgnoreCase)) return Read(full);
            if (File.Exists(target) || Directory.Exists(target)) throw new Exception("已有同名文件，请换一个名称。");
            if (Path.GetDirectoryName(full) != Path.GetDirectoryName(target)) throw new Exception("重命名只能在原公司目录内进行。");
            Backup(full, "重命名前"); File.Move(full, target);
            ReplaceFavorite(Relative(full), Relative(target));
            return Read(target);
        }
        if (action == "delete") {
            string full = SafeMd(Str(a, "path")); Expected(full, Str(a, "version"));
            Backup(full, "删除前"); File.Delete(full); RemoveFavorite(Relative(full)); return new { deleted = true };
        }
        if (action == "restore") {
            string key = Str(a, "key"), backup = Safe(key, true);
            string relative = key.Replace('\\', '/');
            if (!relative.StartsWith(BackupDir + "/", StringComparison.Ordinal) || !relative.EndsWith(".bak", StringComparison.OrdinalIgnoreCase)) throw new Exception("备份名称无效。");
            Match m = Regex.Match(relative.Substring(BackupDir.Length+1), @"^(.*\.md)\.\d{8}T\d{9}Z-[a-f0-9]{8}\.(保存前|删除前|重命名前|恢复前)\.bak$");
            if (!m.Success) throw new Exception("无法识别备份。");
            string target = SafeMd(m.Groups[1].Value); byte[] bytes = File.ReadAllBytes(backup);
            Decode(bytes);
            if (File.Exists(target)) Backup(target, "恢复前");
            Directory.CreateDirectory(Path.GetDirectoryName(target)); AtomicWrite(target, bytes); return Read(target);
        }
        throw new Exception("未知操作。");
    }

    static string HttpText(string method, string url, Dictionary<string, string> headers = null, string body = null) {
        HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
        request.Method = method;
        request.Timeout = 90000;
        request.ReadWriteTimeout = 90000;
        request.UserAgent = "GreetingConfig/1.0";
        if (headers != null) foreach (KeyValuePair<string, string> header in headers) {
            if (header.Key == "Content-Type") request.ContentType = header.Value;
            else request.Headers[header.Key] = header.Value;
        }
        if (body != null) {
            byte[] data = Utf8.GetBytes(body);
            request.ContentLength = data.Length;
            using (Stream stream = request.GetRequestStream()) stream.Write(data, 0, data.Length);
        }
        try {
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            using (StreamReader reader = new StreamReader(response.GetResponseStream(), Utf8)) return reader.ReadToEnd();
        } catch (WebException error) {
            string detail = "";
            if (error.Response != null) using (StreamReader reader = new StreamReader(error.Response.GetResponseStream(), Utf8)) detail = reader.ReadToEnd();
            throw new Exception("外部接口请求失败：" + (String.IsNullOrWhiteSpace(detail) ? error.Message : detail.Substring(0, Math.Min(detail.Length, 500))));
        }
    }

    static object SyncthingStatus(bool toggle) {
        string configPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Syncthing", "config.xml");
        if (!File.Exists(configPath)) return new { available = false, paused = true, state = "not-found", reason = "本机未找到 Syncthing 配置" };
        XmlDocument document = new XmlDocument();
        document.Load(configPath);
        XmlNode guiNode = document.SelectSingleNode("/configuration/gui/address");
        XmlNode keyNode = document.SelectSingleNode("/configuration/gui/apikey");
        if (guiNode == null || keyNode == null) return new { available = false, paused = true, state = "not-found", reason = "Syncthing 配置不完整" };
        string address = guiNode.InnerText.Trim();
        if (address.StartsWith("0.0.0.0:")) address = "127.0.0.1:" + address.Substring(8);
        string origin = address.StartsWith("http://", StringComparison.OrdinalIgnoreCase) || address.StartsWith("https://", StringComparison.OrdinalIgnoreCase) ? address : "http://" + address;
        origin = origin.TrimEnd('/');
        Dictionary<string, string> headers = new Dictionary<string, string> { { "X-API-Key", keyNode.InnerText.Trim() } };
        string folderId = null;
        IList folderItems = Json.DeserializeObject(HttpText("GET", origin + "/rest/config/folders", headers)) as IList;
        if (folderItems == null) return new { available = false, paused = true, state = "not-found", reason = "无法读取 Syncthing 文件夹配置" };
        foreach (object item in folderItems) {
            Dictionary<string, object> folder = item as Dictionary<string, object>;
            if (folder == null || Str(folder, "path").Length == 0) continue;
            string folderPath;
            try { folderPath = Path.GetFullPath(Str(folder, "path")).TrimEnd(Path.DirectorySeparatorChar); }
            catch { continue; }
            if (folderPath.Equals(Path.GetFullPath(Root).TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase)) {
                folderId = Str(folder, "id");
                break;
            }
        }
        if (String.IsNullOrEmpty(folderId)) return new { available = false, paused = true, state = "not-configured", reason = "当前目录未加入 Syncthing" };
        string folderUrl = origin + "/rest/config/folders/" + Uri.EscapeDataString(folderId);
        Dictionary<string, object> settings = Json.Deserialize<Dictionary<string, object>>(HttpText("GET", folderUrl, headers));
        bool paused = Convert.ToBoolean(settings["paused"]);
        if (toggle) {
            HttpText("PATCH", folderUrl, new Dictionary<string, string>(headers) { { "Content-Type", "application/json; charset=utf-8" } }, Json.Serialize(new { paused = !paused }));
            paused = !paused;
        }
        string state = "unknown";
        try {
            Dictionary<string, object> status = Json.Deserialize<Dictionary<string, object>>(HttpText("GET", origin + "/rest/db/status?folder=" + Uri.EscapeDataString(folderId), headers));
            state = Str(status, "state");
        } catch { }
        return new { available = true, paused = paused, state = paused ? "paused" : state, folder = new DirectoryInfo(Root).Name };
    }

    static string FavoritesPath() { return Path.Combine(LocalDir, "favorites-" + RootHash + ".json"); }
    static string SecretPath() { return Path.Combine(LocalDir, "deepseek.key"); }

    static string[] LoadFavorites() {
        string file = FavoritesPath();
        if (!File.Exists(file)) return new string[0];
        try {
            string[] values = Json.Deserialize<string[]>(File.ReadAllText(file, Utf8));
            List<string> valid = new List<string>();
            foreach (string value in values) {
                try { string full = SafeMd(value); if (File.Exists(full) && !valid.Contains(value)) valid.Add(value); } catch { }
            }
            return valid.ToArray();
        } catch { return new string[0]; }
    }

    static void SaveFavorites(IEnumerable<string> paths) {
        Directory.CreateDirectory(LocalDir);
        string file = FavoritesPath(), temp = file + "." + RandomId(6) + ".tmp";
        File.WriteAllText(temp, Json.Serialize(new List<string>(paths)), Utf8);
        if (File.Exists(file)) File.Replace(temp, file, null); else File.Move(temp, file);
    }

    static object ToggleFavorite(string path) {
        string full = SafeMd(path);
        if (!File.Exists(full)) throw new Exception("岗位文件不存在。");
        List<string> paths = new List<string>(LoadFavorites());
        bool favorite;
        if (paths.Contains(path)) { paths.Remove(path); favorite = false; }
        else { paths.Add(path); favorite = true; }
        SaveFavorites(paths);
        return new { favorite = favorite, paths = paths };
    }

    static void ReplaceFavorite(string oldPath, string newPath) {
        List<string> paths = new List<string>(LoadFavorites());
        int index = paths.IndexOf(oldPath);
        if (index < 0) return;
        paths[index] = newPath;
        SaveFavorites(paths);
    }

    static void RemoveFavorite(string path) {
        List<string> paths = new List<string>(LoadFavorites());
        if (paths.Remove(path)) SaveFavorites(paths);
    }

    static void SetAiKey(string key) {
        key = (key ?? "").Trim();
        if (key.Length < 20 || !key.StartsWith("sk-", StringComparison.OrdinalIgnoreCase)) throw new Exception("DeepSeek API Key 格式无效。");
        byte[] encrypted = ProtectedData.Protect(Utf8.GetBytes(key), null, DataProtectionScope.CurrentUser);
        Directory.CreateDirectory(LocalDir);
        File.WriteAllBytes(SecretPath(), encrypted);
    }

    static string LoadAiKey() {
        if (!String.IsNullOrWhiteSpace(EmbeddedAiKey)) return EmbeddedAiKey;
        string file = SecretPath();
        if (!File.Exists(file)) throw new Exception("尚未配置 DeepSeek API Key。");
        try { return Utf8.GetString(ProtectedData.Unprotect(File.ReadAllBytes(file), null, DataProtectionScope.CurrentUser)); }
        catch { throw new Exception("DeepSeek API Key 无法读取，请重新配置。"); }
    }

    static List<Dictionary<string, object>> OverpassPlaces(string query) {
        string queryFile = Path.Combine(LocalDir, "overpass-" + RandomId(8) + ".txt"), raw;
        File.WriteAllText(queryFile, query, Utf8);
        try {
            ProcessStartInfo start = new ProcessStartInfo("curl.exe");
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.RedirectStandardOutput = true;
            start.RedirectStandardError = true;
            start.Arguments = "-sS --fail --max-time 100 -A \"GreetingConfig/1.0\" -H \"Accept: application/json\" --data-urlencode \"data@" + queryFile + "\" https://overpass-api.de/api/interpreter";
            using (Process process = Process.Start(start)) {
                string output = process.StandardOutput.ReadToEnd();
                string error = process.StandardError.ReadToEnd();
                if (!process.WaitForExit(105000)) { try { process.Kill(); } catch { } throw new Exception("地图查询超时，请稍后重试。"); }
                if (process.ExitCode != 0 || String.IsNullOrWhiteSpace(output)) throw new Exception("地图查询失败：" + (String.IsNullOrWhiteSpace(error) ? "无返回结果" : error.Substring(0, Math.Min(error.Length, 300))));
                raw = output;
            }
        } finally { try { File.Delete(queryFile); } catch { } }
        Dictionary<string, object> response = Json.Deserialize<Dictionary<string, object>>(raw);
        IList elements = response.ContainsKey("elements") ? response["elements"] as IList : null;
        List<Dictionary<string, object>> places = new List<Dictionary<string, object>>();
        if (elements == null) return places;
        foreach (object item in elements) {
            Dictionary<string, object> element = item as Dictionary<string, object>;
            if (element == null) continue;
            Dictionary<string, object> tags = element.ContainsKey("tags") ? element["tags"] as Dictionary<string, object> : null;
            Dictionary<string, object> center = element.ContainsKey("center") ? element["center"] as Dictionary<string, object> : null;
            if (tags == null || center == null || !tags.ContainsKey("name")) continue;
            double lat, lon;
            if (!Double.TryParse(Convert.ToString(center["lat"]), NumberStyles.Float, CultureInfo.InvariantCulture, out lat)
                || !Double.TryParse(Convert.ToString(center["lon"]), NumberStyles.Float, CultureInfo.InvariantCulture, out lon)) continue;
            places.Add(new Dictionary<string, object> {
                { "name", Convert.ToString(tags["name"]).Trim() },
                { "level", tags.ContainsKey("admin_level") ? Convert.ToString(tags["admin_level"]) : "" },
                { "lat", lat },
                { "lon", lon }
            });
        }
        return places;
    }

    static double DistanceKm(double lat1, double lon1, double lat2, double lon2) {
        const double radius = 6371.0;
        double dLat = (lat2-lat1)*Math.PI/180.0, dLon = (lon2-lon1)*Math.PI/180.0;
        double a = Math.Sin(dLat/2)*Math.Sin(dLat/2) + Math.Cos(lat1*Math.PI/180.0)*Math.Cos(lat2*Math.PI/180.0)*Math.Sin(dLon/2)*Math.Sin(dLon/2);
        return radius * 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1-a));
    }

    static List<Dictionary<string, object>> LoadAreaIndex() {
        if (AreaIndexCache != null) return AreaIndexCache;
        string raw = HttpText("GET", "https://geo.datav.aliyun.com/areas_v3/bound/all.json");
        IList items = Json.DeserializeObject(raw) as IList;
        AreaIndexCache = new List<Dictionary<string, object>>();
        if (items != null) foreach (object item in items) {
            Dictionary<string, object> entry = item as Dictionary<string, object>;
            if (entry != null) AreaIndexCache.Add(entry);
        }
        return AreaIndexCache;
    }

    static List<Dictionary<string, object>> LoadBoundary(int adcode) {
        List<Dictionary<string, object>> cached;
        if (AreaBoundaryCache.TryGetValue(adcode, out cached)) return cached;
        cached = new List<Dictionary<string, object>>();
        try {
            string raw = HttpText("GET", "https://geo.datav.aliyun.com/areas_v3/bound/" + adcode + "_full.json");
            Dictionary<string, object> collection = Json.Deserialize<Dictionary<string, object>>(raw);
            IList features = collection.ContainsKey("features") ? collection["features"] as IList : null;
            if (features != null) foreach (object item in features) {
                Dictionary<string, object> feature = item as Dictionary<string, object>;
                if (feature != null) cached.Add(feature);
            }
        } catch (Exception error) {
            if (adcode == 100000) throw new Exception("行政区划数据加载失败：" + error.Message);
        }
        AreaBoundaryCache[adcode] = cached;
        return cached;
    }

    static Dictionary<string, object> FeatureProperties(Dictionary<string, object> feature) {
        return feature != null && feature.ContainsKey("properties") ? feature["properties"] as Dictionary<string, object> : null;
    }

    static void CollectRings(object node, List<List<double[]>> rings) {
        IList list = node as IList;
        if (list == null || list.Count == 0) return;
        IList firstPoint = list[0] as IList;
        bool isRing = list[0] is string || (firstPoint != null && firstPoint.Count >= 2 && !(firstPoint[0] is IList));
        if (isRing) {
            List<double[]> ring = new List<double[]>();
            foreach (object point in list) {
                double lon, lat;
                if (point is string) {
                    string[] parts = Convert.ToString(point).Trim().Split(' ');
                    if (parts.Length >= 2 && Double.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out lon)
                        && Double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out lat)) ring.Add(new[] { lon, lat });
                } else {
                    IList values = point as IList;
                    if (values != null && values.Count >= 2
                        && Double.TryParse(Convert.ToString(values[0]), NumberStyles.Float, CultureInfo.InvariantCulture, out lon)
                        && Double.TryParse(Convert.ToString(values[1]), NumberStyles.Float, CultureInfo.InvariantCulture, out lat)) ring.Add(new[] { lon, lat });
                }
            }
            if (ring.Count >= 3) rings.Add(ring);
            return;
        }
        foreach (object child in list) CollectRings(child, rings);
    }

    static bool PointInRing(double lat, double lon, List<double[]> ring) {
        bool inside = false;
        for (int i = 0, j = ring.Count-1; i < ring.Count; j = i++) {
            double xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
            if (((yi > lat) != (yj > lat)) && (lon < (xj-xi)*(lat-yi)/(yj-yi)+xi)) inside = !inside;
        }
        return inside;
    }

    static double SegmentDistanceKm(double lat, double lon, double[] a, double[] b) {
        double scaleX = 111.32 * Math.Cos(lat * Math.PI / 180.0), scaleY = 110.57;
        double ax = (a[0]-lon)*scaleX, ay = (a[1]-lat)*scaleY, bx = (b[0]-lon)*scaleX, by = (b[1]-lat)*scaleY;
        double dx = bx-ax, dy = by-ay, length = dx*dx+dy*dy;
        double t = length == 0 ? 0 : Math.Max(0, Math.Min(1, -(ax*dx+ay*dy)/length));
        double px = ax+t*dx, py = ay+t*dy;
        return Math.Sqrt(px*px+py*py);
    }

    static double MinDistanceToFeature(double lat, double lon, Dictionary<string, object> feature) {
        Dictionary<string, object> geometry = feature != null && feature.ContainsKey("geometry") ? feature["geometry"] as Dictionary<string, object> : null;
        if (geometry == null || !geometry.ContainsKey("coordinates")) return Double.MaxValue;
        List<List<double[]>> rings = new List<List<double[]>>();
        CollectRings(geometry["coordinates"], rings);
        if (rings.Count == 0) return Double.MaxValue;
        if (rings.Any(ring => PointInRing(lat, lon, ring))) return 0;
        double nearest = Double.MaxValue;
        foreach (List<double[]> ring in rings) {
            for (int index = 0; index < ring.Count; index++) {
                double distance = SegmentDistanceKm(lat, lon, ring[index], ring[(index+1)%ring.Count]);
                if (distance < nearest) nearest = distance;
            }
        }
        return nearest;
    }

    static string NormalizeAreaName(string name) {
        name = (name ?? "").Trim();
        return Regex.Replace(name, @"(特别行政区|自治区|自治州|自治县|自治旗|省|市|区|县|旗|盟)$", "");
    }

    static object ExpandLocationsByMap(string content, string radiusText) {
        double radius;
        if (!Double.TryParse(radiusText, NumberStyles.Float, CultureInfo.InvariantCulture, out radius) || radius < 1 || radius > 200) throw new Exception("查询半径应为 1–200 公里。");
        List<string> names = new List<string>();
        foreach (string item in Regex.Split(content, @"[、，,；;\r\n]+")) {
            string name = item.Trim();
            if (name.Length > 0 && !names.Contains(name)) names.Add(name);
        }
        if (names.Count == 0) throw new Exception("请先填写至少一个中心地点。");
        List<Dictionary<string, object>> centers = new List<Dictionary<string, object>>();
        List<string> matchedNames = new List<string>();
        List<Dictionary<string, object>> index = LoadAreaIndex();
        foreach (string inputName in names) {
            string normalized = NormalizeAreaName(inputName);
            List<Dictionary<string, object>> matches = index.Where(area => Convert.ToString(area.ContainsKey("name") ? area["name"] : "") == inputName).ToList();
            if (matches.Count == 0 && normalized.Length >= 2) {
                matches = index.Where(area => {
                    string areaName = NormalizeAreaName(Convert.ToString(area.ContainsKey("name") ? area["name"] : ""));
                    return areaName == normalized || areaName.StartsWith(normalized, StringComparison.Ordinal) || areaName.Contains(normalized);
                }).OrderBy(area => NormalizeAreaName(Convert.ToString(area["name"])) == normalized ? 0 : NormalizeAreaName(Convert.ToString(area["name"])).StartsWith(normalized, StringComparison.Ordinal) ? 1 : 2)
                  .ThenBy(area => Convert.ToString(area["name"]).Length).Take(5).ToList();
            }
            foreach (Dictionary<string, object> area in matches) {
                string actualName = Convert.ToString(area["name"]);
                double lat, lng;
                if (Double.TryParse(Convert.ToString(area["lat"]), NumberStyles.Float, CultureInfo.InvariantCulture, out lat)
                    && Double.TryParse(Convert.ToString(area["lng"]), NumberStyles.Float, CultureInfo.InvariantCulture, out lng)) {
                    centers.Add(new Dictionary<string, object> { { "name", actualName }, { "lat", lat }, { "lon", lng } });
                    if (!matchedNames.Contains(actualName)) matchedNames.Add(actualName);
                }
            }
        }
        if (centers.Count == 0) throw new Exception("地图数据未找到已填写地点，请检查名称后重试。");
        if (centers.Count > 40) centers = centers.GetRange(0, 40);
        Dictionary<string, double> result = new Dictionary<string, double>();
        Action<Dictionary<string, object>, string> addFeature = (feature, level) => {
            Dictionary<string, object> properties = FeatureProperties(feature);
            if (properties == null || !properties.ContainsKey("name")) return;
            string name = Convert.ToString(properties["name"]).Trim();
            if (String.IsNullOrWhiteSpace(name)) return;
            double nearest = Double.MaxValue;
            foreach (Dictionary<string, object> center in centers) nearest = Math.Min(nearest, MinDistanceToFeature(Convert.ToDouble(center["lat"], CultureInfo.InvariantCulture), Convert.ToDouble(center["lon"], CultureInfo.InvariantCulture), feature));
            if (nearest <= radius && (!result.ContainsKey(name) || nearest < result[name])) result[name] = nearest;
        };
        foreach (Dictionary<string, object> province in LoadBoundary(100000)) {
            double provinceDistance = centers.Min(center => MinDistanceToFeature(Convert.ToDouble(center["lat"], CultureInfo.InvariantCulture), Convert.ToDouble(center["lon"], CultureInfo.InvariantCulture), province));
            if (provinceDistance > radius) continue;
            Dictionary<string, object> provinceProperties = FeatureProperties(province);
            int provinceCode;
            if (provinceProperties == null || !Int32.TryParse(Convert.ToString(provinceProperties["adcode"]), out provinceCode)) continue;
            List<int> cityCodes = new List<int>();
            foreach (Dictionary<string, object> feature in LoadBoundary(provinceCode)) {
                Dictionary<string, object> properties = FeatureProperties(feature);
                string level = properties != null && properties.ContainsKey("level") ? Convert.ToString(properties["level"]) : "";
                if (level == "city") {
                    double distance = centers.Min(center => MinDistanceToFeature(Convert.ToDouble(center["lat"], CultureInfo.InvariantCulture), Convert.ToDouble(center["lon"], CultureInfo.InvariantCulture), feature));
                    if (distance <= radius) {
                        addFeature(feature, level);
                        int cityCode;
                        if (Int32.TryParse(Convert.ToString(properties["adcode"]), out cityCode) && !cityCodes.Contains(cityCode)) cityCodes.Add(cityCode);
                    }
                } else if (level == "district") addFeature(feature, level);
            }
            foreach (int cityCode in cityCodes) foreach (Dictionary<string, object> district in LoadBoundary(cityCode)) {
                Dictionary<string, object> properties = FeatureProperties(district);
                if (properties != null && Convert.ToString(properties["level"]) == "district") addFeature(district, "district");
            }
        }
        List<string> locations = new List<string>(result.Keys);
        locations.Sort((left, right) => result[left].CompareTo(result[right]));
        return new { locations = locations, provider = "阿里云 DataV 行政区划", radius = radius, centers = matchedNames };
    }

    static object AiExpand(Dictionary<string, object> input) {
        string kind = Str(input, "kind");
        string content = Str(input, "text");
        string stage = Str(input, "stage");
        string radius = Str(input, "radius");
        if (content.Length > 12000) throw new Exception("待扩充内容过长，请减少后再试。");
        if (kind == "locations") return ExpandLocationsByMap(content, radius);
        string key = LoadAiKey();
        string prompt;
        if (kind == "lexicon") {
            prompt = "你是招聘筛选词库助手。根据已有词库增加同层级、可替代或并列关系的近义词、产品类别和岗位类别。"
                + "禁止把已有词作为前缀或词根派生出角色、系统、运维、实施、调试、应用、项目管理、方案设计、系统集成等组合词。"
                + "例如已有 AGV 时，应补充 AMR、移动机器人、搬运机器人、潜伏车、叉举车、CTU、STU 等，而不是 AGV小车、AGV机器人、AGV调度系统。"
                + "列表卡片阶段侧重岗位、职责、经验等短词；电子简历阶段侧重技能、软件、流程和工具。"
                + "保留已有分组。只返回严格 JSON，格式为 {\"groups\":{\"A\":[\"词1\",\"词2\"]}}。"
                + "已有分组名必须原样使用；没有分组时使用 A。每组最多增加 10 个去重词。\n阶段：" + (stage == "resume" ? "电子简历" : "列表卡片") + "\n已有词库：\n" + content;
        } else throw new Exception("未知的 AI 扩充类型。");
        object requestBody = new {
            model = "deepseek-chat",
            temperature = 0.2,
            max_tokens = 1400,
            response_format = new { type = "json_object" },
            messages = new object[] {
                new { role = "system", content = "只返回有效 JSON，不得包含 Markdown 代码块或解释。" },
                new { role = "user", content = prompt }
            }
        };
        Dictionary<string, string> headers = new Dictionary<string, string> {
            { "Authorization", "Bearer " + key },
            { "Content-Type", "application/json; charset=utf-8" }
        };
        string raw = HttpText("POST", "https://api.deepseek.com/chat/completions", headers, Json.Serialize(requestBody));
        Dictionary<string, object> response = Json.Deserialize<Dictionary<string, object>>(raw);
        IList choices = response.ContainsKey("choices") ? response["choices"] as IList : null;
        if (choices == null || choices.Count == 0) throw new Exception("DeepSeek 未返回有效结果。");
        Dictionary<string, object> choice = choices[0] as Dictionary<string, object>;
        Dictionary<string, object> message = choice != null && choice.ContainsKey("message") ? choice["message"] as Dictionary<string, object> : null;
        string answer = message != null && message.ContainsKey("content") ? Convert.ToString(message["content"]).Trim() : "";
        answer = Regex.Replace(answer, "^```(?:json)?\\s*", "", RegexOptions.IgnoreCase).Replace("```", "").Trim();
        Dictionary<string, object> payload;
        try { payload = Json.Deserialize<Dictionary<string, object>>(answer); }
        catch { throw new Exception("DeepSeek 返回的结果格式异常，请重试。"); }
        if (kind == "lexicon") {
            Dictionary<string, object> groups = payload.ContainsKey("groups") ? payload["groups"] as Dictionary<string, object> : payload;
            if (groups == null) throw new Exception("DeepSeek 未返回词库分组。");
            Dictionary<string, object> cleanGroups = new Dictionary<string, object>();
            List<string> existingWords = new List<string>();
            foreach (string line in Regex.Split(content, @"\r?\n")) {
                string plain = Regex.Replace(line, @"^(?:匹配方式|组合|[A-Za-z][0-9]*)\s*[：:]\s*", "").Trim();
                foreach (string item in Regex.Split(plain, @"[、，,；;]+")) if (item.Trim().Length >= 2) existingWords.Add(item.Trim());
            }
            foreach (KeyValuePair<string, object> group in groups) {
                IList values = group.Value as IList;
                if (values == null) continue;
                List<string> clean = new List<string>();
                foreach (object value in values) {
                    string word = Convert.ToString(value).Trim();
                    bool nested = existingWords.Any(existing => !existing.Equals(word, StringComparison.OrdinalIgnoreCase)
                        && word.IndexOf(existing, StringComparison.OrdinalIgnoreCase) >= 0);
                    if (word.Length > 0 && word.Length <= 30 && !nested && !clean.Contains(word)) clean.Add(word);
                    if (clean.Count >= 10) break;
                }
                cleanGroups[group.Key.Trim().ToUpperInvariant()] = clean;
            }
            return new { groups = cleanGroups, provider = "DeepSeek" };
        }
        IList locations = payload.ContainsKey("locations") ? payload["locations"] as IList : null;
        List<string> cleanLocations = new List<string>();
        if (locations != null) foreach (object value in locations) {
            string location = Convert.ToString(value).Trim();
            if (location.Length > 0 && location.Length <= 30 && !cleanLocations.Contains(location)) cleanLocations.Add(location);
        }
        return new { locations = cleanLocations, provider = "DeepSeek" };
    }

    static void Scan(string directory, List<object> files, List<string> dirs) {
        foreach (string sub in Directory.GetDirectories(directory)) {
            if (Path.GetFileName(sub).StartsWith(".") || IsLink(sub)) continue;
            dirs.Add(Relative(sub)); Scan(sub, files, dirs);
        }
        foreach (string f in Directory.GetFiles(directory, "*.md")) {
            if (Path.GetFileName(f).StartsWith(".") || IsLink(f)) continue;
            try { files.Add(Read(f)); } catch (Exception e) { throw new Exception("无法读取 " + Relative(f) + "：" + e.Message); }
        }
    }
    static void ScanHistory(string dir, List<object> result) {
        foreach (string sub in Directory.GetDirectories(dir)) if (!IsLink(sub)) ScanHistory(sub, result);
        foreach (string f in Directory.GetFiles(dir, "*.bak")) {
            if (IsLink(f)) continue;
            string rel = Relative(f).Substring(BackupDir.Length+1);
            Match m = Regex.Match(rel, @"^(.*\.md)\.(\d{8}T\d{9}Z)-[a-f0-9]{8}\.(保存前|删除前|重命名前|恢复前)\.bak$");
            if (!m.Success) continue;
            result.Add(new { key = Relative(f), path = m.Groups[1].Value, stamp = m.Groups[2].Value, reason = m.Groups[3].Value, time = File.GetLastWriteTime(f).ToString("yyyy-MM-dd HH:mm:ss") });
        }
    }
    static object Read(string full) {
        byte[] data = File.ReadAllBytes(full);
        if (data.Length > 8000000) throw new Exception("单个配置文件不能超过 8 MB。");
        return new { path = Relative(full), name = Path.GetFileName(full), text = Decode(data), bom = HasBom(data), version = Hash(data), size = data.Length, modified = File.GetLastWriteTime(full).ToString("yyyy-MM-dd HH:mm:ss") };
    }
    static byte[] Expected(string full, string version) {
        byte[] data = File.ReadAllBytes(full);
        if (String.IsNullOrEmpty(version) || Hash(data) != version) throw new Exception("文件已被其他程序修改。请先复制未保存内容，再刷新后重新编辑，避免覆盖其他修改。");
        return data;
    }
    static void Backup(string full, string reason) {
        string stamp = DateTime.UtcNow.ToString("yyyyMMdd'T'HHmmssfff'Z'") + "-" + RandomId(4);
        string target = Safe(BackupDir + "/" + Relative(full) + "." + stamp + "." + reason + ".bak", true);
        Directory.CreateDirectory(Path.GetDirectoryName(target)); File.Copy(full, target, false);
    }
    static void AtomicWrite(string full, byte[] bytes) {
        string tmp = Path.Combine(Path.GetDirectoryName(full), ".config-" + RandomId(12) + ".tmp");
        try { File.WriteAllBytes(tmp, bytes); if (File.Exists(full)) File.Replace(tmp, full, null); else File.Move(tmp, full); }
        finally { if (File.Exists(tmp)) File.Delete(tmp); }
    }
    static string SafeMd(string input) {
        if (!input.EndsWith(".md", StringComparison.OrdinalIgnoreCase)) throw new Exception("只能操作 Markdown 文件。");
        return Safe(input, false);
    }
    static string Safe(string input, bool backups) {
        if (String.IsNullOrWhiteSpace(input) || Path.IsPathRooted(input)) throw new Exception("路径无效。");
        string[] parts = input.Replace('\\', '/').Split('/');
        for (int i = 0; i < parts.Length; i++) {
            string p = parts[i];
            if (p.Length == 0 || p == "." || p == ".." || p.EndsWith(".") || p.EndsWith(" ") || p.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || Regex.IsMatch(p, @"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", RegexOptions.IgnoreCase)) throw new Exception("文件或目录名称无效。");
            if (p.StartsWith(".") && !(backups && i == 0 && p == BackupDir)) throw new Exception("不能访问隐藏目录或文件。");
        }
        string full = Path.GetFullPath(Path.Combine(Root, String.Join(Path.DirectorySeparatorChar.ToString(), parts)));
        if (!full.StartsWith(Root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new Exception("路径超出配置目录。");
        string check = Root;
        foreach (string p in parts) { check = Path.Combine(check, p); if ((File.Exists(check) || Directory.Exists(check)) && IsLink(check)) throw new Exception("不能操作链接目录或链接文件。"); }
        return full;
    }
    static bool IsLink(string path) { return (File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0; }
    static string Relative(string full) { return full.Substring(Root.Length+1).Replace('\\', '/'); }
    static bool HasBom(byte[] data) { return data.Length >= 3 && data[0] == 239 && data[1] == 187 && data[2] == 191; }
    static string Decode(byte[] data) { int bom = HasBom(data) ? 3 : 0; return Utf8.GetString(data, bom, data.Length-bom); }
    static byte[] Encode(string text, bool bom) { return Utf8.GetBytes((bom ? "\uFEFF" : "") + text); }
    static string Str(Dictionary<string, object> a, string key) { object value; return a.TryGetValue(key, out value) && value != null ? Convert.ToString(value) : ""; }
    static string Hash(byte[] bytes) { using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }
    static string RandomId(int length) { byte[] b = new byte[length]; using (RandomNumberGenerator r = RandomNumberGenerator.Create()) r.GetBytes(b); return BitConverter.ToString(b).Replace("-", "").ToLowerInvariant(); }
}
