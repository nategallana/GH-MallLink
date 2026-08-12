using System;
using System.IO;
using System.Text;
using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;

namespace GH_Mall_Linking.Services
{
    public class LogService
    {
        private readonly string _logFolderPath;

        public LogService()
        {
            _logFolderPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Logs");
            if (!Directory.Exists(_logFolderPath))
            {
                Directory.CreateDirectory(_logFolderPath);
            }
        }

        public void LogInfo(string message, string module = "General")
        {
            WriteLog("INFO", message, module);
        }

        public void LogWarning(string message, string module = "General")
        {
            WriteLog("WARN", message, module);
        }

        public void LogError(string message, Exception? ex = null, string module = "General")
        {
            string fullMessage = ex != null
                ? $"{message} | Exception: {ex.Message} | StackTrace: {ex.StackTrace}"
                : message;
            WriteLog("ERROR", fullMessage, module);
        }

        public void LogDebug(string message, string module = "General")
        {
            WriteLog("DEBUG", message, module);
        }

        private void WriteLog(string level, string message, string module)
        {
            string? dbFailureDetail = null;
            string cleanModule = string.IsNullOrWhiteSpace(module) ? "General" : module;

            try
            {
                // 1. Write directly to SQLite local database (AppDbContext)
                using (var db = new AppDbContext())
                {
                    var logEntry = new Log
                    {
                        Timestamp = DateTime.Now,
                        Level = level ?? "INFO",
                        Source = cleanModule, // Populates 'Source' directly (prevents NOT NULL constraint error)
                        Message = message ?? string.Empty
                    };

                    db.Logs.Add(logEntry);
                    db.SaveChanges();
                }
            }
            catch (Exception dbEx)
            {
                dbFailureDetail = $"{dbEx.GetType().Name}: {dbEx.Message}";

                Exception? inner = dbEx.InnerException;
                while (inner != null)
                {
                    dbFailureDetail += $" --> Inner: {inner.Message}";
                    inner = inner.InnerException;
                }
            }

            try
            {
                // 2. Write to daily text log file in /Logs folder
                string logFile = Path.Combine(_logFolderPath, $"EOD_{DateTime.Now:yyyyMMdd}.txt");
                string logLine = $"[{DateTime.Now:yyyy-MM-dd HH:mm:ss}] [{level}] [{cleanModule}] {message}{Environment.NewLine}";

                if (dbFailureDetail != null)
                {
                    logLine += $"    (DB write failed: {dbFailureDetail}){Environment.NewLine}";
                }

                File.AppendAllText(logFile, logLine, Encoding.UTF8);
            }
            catch
            {
                // Suppress file write errors to keep application robust
            }
        }
    }
}