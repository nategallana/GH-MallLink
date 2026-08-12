using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;

namespace GH_Mall_Linking.Services
{
    public class PythonBridgeService
    {
        private readonly ConfigService _configService;

        public PythonBridgeService()
        {
            _configService = new ConfigService();
        }

        /// <summary>
        /// Executes a specified Python script asynchronously with given arguments.
        /// </summary>
        public async Task<string> RunPythonScriptAsync(string scriptNameWithoutExtension, string arguments)
        {
            return await Task.Run(() =>
            {
                try
                {
                    string basePath = AppDomain.CurrentDomain.BaseDirectory;

                    // Format script filename
                    string scriptFileName = scriptNameWithoutExtension.EndsWith(".py", StringComparison.OrdinalIgnoreCase)
                        ? scriptNameWithoutExtension
                        : $"{scriptNameWithoutExtension}.py";

                    // Check subfolder "PythonEngine" first, then fallback to BaseDirectory
                    string scriptPath = Path.Combine(basePath, "PythonEngine", scriptFileName);
                    if (!File.Exists(scriptPath))
                    {
                        scriptPath = Path.Combine(basePath, scriptFileName);
                    }

                    if (!File.Exists(scriptPath))
                    {
                        return $"[Error] Python script not found at path: {scriptPath}";
                    }

                    // Get configured Python executable from Settings DB
                    string pythonExecutable = _configService.GetValue("PythonPath", @"C:\Python39\python.exe");

                    if (string.IsNullOrWhiteSpace(pythonExecutable) ||
                       (!pythonExecutable.Equals("python", StringComparison.OrdinalIgnoreCase) && !File.Exists(pythonExecutable)))
                    {
                        pythonExecutable = "python"; // Fallback to system PATH
                    }

                    // Script path MUST be passed as the first argument to python.exe
                    string fullArguments = $"\"{scriptPath}\" {arguments}";

                    ProcessStartInfo startInfo = new ProcessStartInfo
                    {
                        FileName = pythonExecutable,
                        Arguments = fullArguments,
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        CreateNoWindow = true
                    };

                    using (Process process = Process.Start(startInfo))
                    {
                        if (process == null) return "[Error] Failed to start Python process.";

                        string output = process.StandardOutput.ReadToEnd();
                        string error = process.StandardError.ReadToEnd();
                        process.WaitForExit();

                        if (!string.IsNullOrWhiteSpace(error) && process.ExitCode != 0)
                        {
                            return $"[Python Error]: {error}";
                        }

                        return string.IsNullOrWhiteSpace(output) ? error : output;
                    }
                }
                catch (Exception ex)
                {
                    return $"[Exception] Failed to execute Python bridge: {ex.Message}";
                }
            });
        }

        // =========================================================================
        // HELPER CONVENIENCE METHODS (Wraps main.py actions dynamically)
        // =========================================================================

        /// <summary>
        /// Triggers Paradox Table Sync using saved configuration paths.
        /// </summary>
        public async Task<string> SyncParadoxAsync()
        {
            string paradoxDir = _configService.GetValue("ParadoxDBFolder", string.Empty);
            string sqliteDbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gh_mall_linking.db");

            string args = $"--action sync --db \"{sqliteDbPath}\" --paradox_dir \"{paradoxDir}\"";
            return await RunPythonScriptAsync("main", args);
        }

        /// <summary>
        /// Triggers Cloud XML Sync for one specific date's subfolder (fast — matches
        /// how the POS organizes its cloud export as one folder per date). Pass null
        /// for a full rebuild across every date subfolder (slow — initial load only).
        /// </summary>
        public async Task<string> SyncCloudAsync(string targetDateYyyyMmDd = null)
        {
            string cloudDir = _configService.GetValue("CloudDataFolder", string.Empty);
            string sqliteDbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gh_mall_linking.db");

            string args = $"--action sync_cloud --db \"{sqliteDbPath}\" --cloud_dir \"{cloudDir}\"";
            if (!string.IsNullOrWhiteSpace(targetDateYyyyMmDd))
            {
                args += $" --target_date \"{targetDateYyyyMmDd}\"";
            }
            return await RunPythonScriptAsync("main", args);
        }

        /// <summary>
        /// Generates EOD text file for a given target date, from the given source
        /// ("paradox" or "cloud").
        /// </summary>
        public async Task<string> GenerateEodAsync(string targetDateYyyyMmDd, string source = "paradox")
        {
            string exportDir = _configService.GetValue("AccLocalFolder", string.Empty);
            string sqliteDbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gh_mall_linking.db");

            string args = $"--action eod --db \"{sqliteDbPath}\" --target_date \"{targetDateYyyyMmDd}\" --export_dir \"{exportDir}\" --source \"{source}\"";
            return await RunPythonScriptAsync("main", args);
        }
    }
}