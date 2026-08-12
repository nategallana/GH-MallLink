using System;
using System.IO;
using System.Threading.Tasks;
using GH_Mall_Linking.Services;

namespace GH_Mall_Linking.Services
{
    public class SyncResult
    {
        public bool Success { get; set; }
        public string Message { get; set; }
    }

    public class SyncService
    {
        private readonly ConfigService _configService;
        private readonly ParadoxSyncService _paradoxSyncService;

        public SyncService()
        {
            _configService = new ConfigService();
            _paradoxSyncService = new ParadoxSyncService();
        }

        public async Task<SyncResult> ExecuteBulkSyncAsync()
        {
            string paradoxDataPath = _configService.GetValue("ParadoxDBFolder", string.Empty);
            string sqliteDbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gh_mall_linking.db");

            if (string.IsNullOrWhiteSpace(paradoxDataPath) || !Directory.Exists(paradoxDataPath))
            {
                return new SyncResult
                {
                    Success = false,
                    Message = $"No valid Paradox database folder is configured!\nPath: '{paradoxDataPath}'"
                };
            }

            try
            {
                string syncLog = string.Empty;

                // Calls Native C# ODBC Sync
                bool success = await Task.Run(() =>
                    _paradoxSyncService.SyncParadoxToSqlite(paradoxDataPath, sqliteDbPath, out syncLog));

                return new SyncResult
                {
                    Success = success,
                    Message = syncLog
                };
            }
            catch (Exception ex)
            {
                return new SyncResult
                {
                    Success = false,
                    Message = $"Sync execution failed:\n{ex.Message}"
                };
            }
        }
    }
}