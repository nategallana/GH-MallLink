using System;
using System.IO;
using System.Threading.Tasks;
using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;

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
            string paradoxDataPath =
                _configService.GetValue("ParadoxDBFolder", string.Empty);

            string sqliteDbPath = Path.Combine(
                AppDomain.CurrentDomain.BaseDirectory,
                "gh_mall_linking.db"
            );

            if (string.IsNullOrWhiteSpace(paradoxDataPath) ||
                !Directory.Exists(paradoxDataPath))
            {
                return new SyncResult
                {
                    Success = false,
                    Message =
                        $"No valid Paradox database folder is configured!\n" +
                        $"Path: '{paradoxDataPath}'"
                };
            }

            SyncHistory history = new SyncHistory
            {
                StartedAt = DateTime.Now,
                Status = "Running",
                OrdersSynced = 0,
                ItemsSynced = 0,
                ErrorDetails = string.Empty
            };

            try
            {
                // ---------------------------------------------------------
                // Create the SyncHistory row BEFORE starting the sync.
                // ---------------------------------------------------------
                using (var db = new AppDbContext())
                {
                    db.SyncHistories.Add(history);
                    db.SaveChanges();
                }

                string syncLog = string.Empty;

                // ---------------------------------------------------------
                // Run the actual Paradox sync.
                // ---------------------------------------------------------
                bool success = await Task.Run(() =>
                    _paradoxSyncService.SyncParadoxToSqlite(
                        paradoxDataPath,
                        sqliteDbPath,
                        out syncLog
                    )
                );

                // ---------------------------------------------------------
                // Update history after the sync completes.
                // ---------------------------------------------------------
                int ordersSynced = 0;
                int itemsSynced = 0;

                ParseSyncCounts(
                    syncLog,
                    out ordersSynced,
                    out itemsSynced
                );

                history.CompletedAt = DateTime.Now;
                history.Status = success ? "Success" : "Failed";
                history.OrdersSynced = ordersSynced;
                history.ItemsSynced = itemsSynced;
                history.ErrorDetails = success ? string.Empty : syncLog;

                using (var db = new AppDbContext())
                {
                    var existing = db.SyncHistories.Find(history.Id);

                    if (existing != null)
                    {
                        existing.CompletedAt = history.CompletedAt;
                        existing.Status = history.Status;
                        existing.OrdersSynced = history.OrdersSynced;
                        existing.ItemsSynced = history.ItemsSynced;
                        existing.ErrorDetails = history.ErrorDetails;

                        db.SaveChanges();
                    }
                }

                return new SyncResult
                {
                    Success = success,
                    Message = syncLog
                };
            }
            catch (Exception ex)
            {
                string errorMessage =
                    $"Sync execution failed:\n{ex}";

                history.CompletedAt = DateTime.Now;
                history.Status = "Failed";
                history.ErrorDetails = errorMessage ?? string.Empty;

                try
                {
                    using (var db = new AppDbContext())
                    {
                        var existing = db.SyncHistories.Find(history.Id);

                        if (existing != null)
                        {
                            existing.CompletedAt = history.CompletedAt;
                            existing.Status = "Failed";
                            existing.OrdersSynced = history.OrdersSynced;
                            existing.ItemsSynced = history.ItemsSynced;
                            existing.ErrorDetails = errorMessage;

                            db.SaveChanges();
                        }
                    }
                }
                catch
                {
                    // Do not hide the original sync exception
                }

                return new SyncResult
                {
                    Success = false,
                    Message = errorMessage
                };
            }
        }

        private static void ParseSyncCounts(
            string syncLog,
            out int ordersSynced,
            out int itemsSynced)
        {
            ordersSynced = 0;
            itemsSynced = 0;

            if (string.IsNullOrWhiteSpace(syncLog))
                return;

            try
            {
                // Expected examples:
                //
                // "Synced 123 orders and 456 items"
                // "123 orders, 456 items"
                //
                // We deliberately keep this tolerant because the
                // ParadoxSyncService log wording may change.

                var orderMatch =
                    System.Text.RegularExpressions.Regex.Match(
                        syncLog,
                        @"(\d+)\s+orders?",
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase
                    );

                var itemMatch =
                    System.Text.RegularExpressions.Regex.Match(
                        syncLog,
                        @"(\d+)\s+items?",
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase
                    );

                if (orderMatch.Success)
                    int.TryParse(
                        orderMatch.Groups[1].Value,
                        out ordersSynced
                    );

                if (itemMatch.Success)
                    int.TryParse(
                        itemMatch.Groups[1].Value,
                        out itemsSynced
                    );
            }
            catch
            {
                // Count parsing must never cause the sync itself to fail.
            }
        }
    }
}