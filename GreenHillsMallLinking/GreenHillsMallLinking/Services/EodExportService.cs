using System;
using System.IO;
using System.Threading.Tasks;

namespace GH_Mall_Linking.Services
{
    public class ExportResult
    {
        public bool Success { get; set; }
        public string FilePath { get; set; }
        public string Message { get; set; }
    }

    public class EodExportService
    {
        private readonly ConfigService _configService;
        private readonly PythonBridgeService _pythonBridge;
        private readonly LogService _logService;

        public EodExportService()
        {
            _configService = new ConfigService();
            _pythonBridge = new PythonBridgeService();
            _logService = new LogService();
        }

        /// <summary>
        /// Executes the Python eod_generator script to generate the Green Hills Mall EOD text/CSV export file.
        /// </summary>
        public async Task<ExportResult> GenerateEodExportAsync(DateTime startDate, DateTime endDate, string source = "paradox")
        {
            try
            {
                string outputDir = _configService.GetValue("ExportFolderPath", Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Exports"));
                string dbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "App_Data", "GH_Mall.db"); // Update with your actual SQLite file path

                if (!Directory.Exists(outputDir))
                {
                    Directory.CreateDirectory(outputDir);
                }

                string startStr = startDate.ToString("yyyy-MM-dd");

                _logService.LogInfo($"Triggering Python EOD Generator for date {startStr} on source: {source}", "EodExportService");

                // Pass 4 Arguments: [dbPath] [targetDate] [exportFolder] [source]
                string arguments = $"\"{dbPath}\" \"{startStr}\" \"{outputDir}\" \"{source.ToLower()}\"";
                string resultOutput = await _pythonBridge.RunPythonScriptAsync("eod_generator", arguments);

                if (resultOutput.Contains("[Error]") || resultOutput.Contains("[Python Errors]"))
                {
                    return new ExportResult
                    {
                        Success = false,
                        Message = $"EOD Export script failed:\n{resultOutput}"
                    };
                }

                return new ExportResult
                {
                    Success = true,
                    FilePath = outputDir,
                    Message = "EOD Export completed successfully!\n" + resultOutput
                };
            }
            catch (Exception ex)
            {
                _logService.LogError($"EOD Export execution error: {ex.Message}", ex, "EodExportService");
                return new ExportResult
                {
                    Success = false,
                    Message = $"Failed to execute EOD export:\n{ex.Message}"
                };
            }
        }
    }
}