using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Text.RegularExpressions;
using System.Threading;

internal static class DiceFrameLauncher
{
    private const string DefaultPort = "18000";
    private static Process serverProcess;

    [STAThread]
    private static int Main(string[] args)
    {
        Console.Title = "DiceFrame";

        string root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        string python = Path.Combine(root, "python", "python.exe");
        string serverScript = Path.Combine(root, "app", "web_server.py");
        string dataDir = Path.Combine(root, "data");
        string logsDir = Path.Combine(root, "logs");

        if (!File.Exists(python))
        {
            return Fail("Cannot find bundled Python: " + python);
        }
        if (!File.Exists(serverScript))
        {
            return Fail("Cannot find DiceFrame server: " + serverScript);
        }

        Directory.CreateDirectory(dataDir);
        Directory.CreateDirectory(logsDir);

        string configPath = Path.Combine(dataDir, "config.json");
        string port = ResolvePort(configPath);
        string url = "http://127.0.0.1:" + port;

        Console.WriteLine("========================================");
        Console.WriteLine("  DiceFrame Portable");
        Console.WriteLine("  " + url);
        Console.WriteLine("========================================");
        Console.WriteLine();

        AppDomain.CurrentDomain.ProcessExit += delegate { StopServer(); };
        Console.CancelKeyPress += delegate(object sender, ConsoleCancelEventArgs eventArgs)
        {
            eventArgs.Cancel = true;
            StopServer();
            Environment.Exit(0);
        };

        try
        {
            serverProcess = StartServer(root, python, serverScript, dataDir);
        }
        catch (Exception ex)
        {
            return Fail("DiceFrame failed to start: " + ex.Message);
        }

        if (WaitForServer(url, TimeSpan.FromSeconds(30)))
        {
            OpenBrowser(url);
            Console.WriteLine("DiceFrame is running. Close this window to stop it.");
            Console.WriteLine();
        }
        else if (serverProcess.HasExited)
        {
            return Fail("DiceFrame exited before the Web UI became ready.");
        }
        else
        {
            Console.WriteLine("DiceFrame is still starting. Open this address manually if the browser does not open:");
            Console.WriteLine(url);
            Console.WriteLine();
        }

        serverProcess.WaitForExit();
        return serverProcess.ExitCode;
    }

    private static Process StartServer(string root, string python, string serverScript, string dataDir)
    {
        ProcessStartInfo info = new ProcessStartInfo();
        info.FileName = python;
        info.Arguments = Quote(serverScript);
        info.WorkingDirectory = root;
        info.UseShellExecute = false;
        info.EnvironmentVariables["TRPG_DATA_DIR"] = dataDir;
        return Process.Start(info);
    }

    private static bool WaitForServer(string url, TimeSpan timeout)
    {
        DateTime deadline = DateTime.UtcNow.Add(timeout);
        while (DateTime.UtcNow < deadline)
        {
            if (serverProcess != null && serverProcess.HasExited)
            {
                return false;
            }
            if (CanOpen(url))
            {
                return true;
            }
            Thread.Sleep(500);
        }
        return false;
    }

    private static bool CanOpen(string url)
    {
        try
        {
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
            request.Method = "GET";
            request.Timeout = 1000;
            request.AllowAutoRedirect = false;
            using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
            {
                int statusCode = (int)response.StatusCode;
                return statusCode >= 200 && statusCode < 500;
            }
        }
        catch
        {
            return false;
        }
    }

    private static void OpenBrowser(string url)
    {
        try
        {
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = url;
            info.UseShellExecute = true;
            Process.Start(info);
        }
        catch
        {
            Console.WriteLine("Open this address in your browser:");
            Console.WriteLine(url);
        }
    }

    private static void StopServer()
    {
        try
        {
            if (serverProcess != null && !serverProcess.HasExited)
            {
                serverProcess.Kill();
                serverProcess.WaitForExit(3000);
            }
        }
        catch
        {
        }
    }

    private static string ResolvePort(string configPath)
    {
        string envPort = Environment.GetEnvironmentVariable("TRPG_WEB_PORT");
        if (IsPort(envPort))
        {
            return envPort;
        }

        try
        {
            if (File.Exists(configPath))
            {
                string text = File.ReadAllText(configPath);
                Match match = Regex.Match(text, "\"web_port\"\\s*:\\s*(\\d+)");
                if (match.Success && IsPort(match.Groups[1].Value))
                {
                    return match.Groups[1].Value;
                }
            }
        }
        catch
        {
        }

        return DefaultPort;
    }

    private static bool IsPort(string value)
    {
        int port;
        return !string.IsNullOrWhiteSpace(value)
            && int.TryParse(value, out port)
            && port >= 1
            && port <= 65535;
    }

    private static string Quote(string value)
    {
        return "\"" + value.Replace("\"", "\\\"") + "\"";
    }

    private static int Fail(string message)
    {
        Console.WriteLine(message);
        Console.WriteLine();
        Console.WriteLine("Press any key to close.");
        Console.ReadKey(true);
        return 1;
    }
}
