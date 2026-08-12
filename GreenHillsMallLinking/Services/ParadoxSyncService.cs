using System;
using System.Data;
using System.Data.Odbc;
using System.IO;
using Microsoft.Data.Sqlite;

namespace GH_Mall_Linking.Services
{
    public class ParadoxSyncService
    {
        private const string PARADOX_PASSWORD = "5A*281";

        public bool SyncParadoxToSqlite(string paradoxFolderPath, string sqliteDbPath, out string logOutput)
        {
            var log = new System.Text.StringBuilder();
            log.AppendLine($"Starting Native C# Paradox Sync from: '{paradoxFolderPath}'");

            if (!Directory.Exists(paradoxFolderPath))
            {
                logOutput = $"Directory does not exist: {paradoxFolderPath}";
                return false;
            }

            int totalOrders = 0;
            int totalItems = 0;
            int totalPayments = 0;

            // Connection string using Microsoft Paradox Driver
            string odbcConnStr = $"Driver={{Microsoft Paradox Driver (*.db )}};DriverID=538;Fil=Paradox 5.X;Dbq={paradoxFolderPath};DefaultDir={paradoxFolderPath};PWD={PARADOX_PASSWORD};";

            using (var sqliteConn = new SqliteConnection($"Data Source={sqliteDbPath}"))
            {
                sqliteConn.Open();
                using (var transaction = sqliteConn.BeginTransaction())
                {
                    try
                    {
                        // Clear previous Paradox staging data
                        using (var cmd = sqliteConn.CreateCommand())
                        {
                            cmd.Transaction = transaction;
                            cmd.CommandText = @"
                                DELETE FROM StagingItems WHERE Source = 'PARADOX';
                                DELETE FROM StagingPayments WHERE Source = 'PARADOX';
                                DELETE FROM StagingOrders WHERE Source = 'PARADOX';";
                            cmd.ExecuteNonQuery();
                        }

                        using (var odbcConn = new OdbcConnection(odbcConnStr))
                        {
                            odbcConn.Open();

                            // 1. SYNC ORDERS
                            totalOrders = SyncOrders(odbcConn, sqliteConn, transaction, log);

                            // 2. SYNC ITEMS
                            totalItems = SyncItems(odbcConn, sqliteConn, transaction, log);

                            // 3. SYNC PAYMENTS
                            totalPayments = SyncPayments(odbcConn, sqliteConn, transaction, log);
                        }

                        transaction.Commit();
                        log.AppendLine($"SUCCESS: Synced {totalOrders} orders, {totalItems} items, and {totalPayments} payments.");
                        logOutput = log.ToString();
                        return true;
                    }
                    catch (Exception ex)
                    {
                        transaction.Rollback();
                        log.AppendLine($"[ERROR] C# Paradox Sync failed: {ex.Message}");
                        logOutput = log.ToString();
                        return false;
                    }
                }
            }
        }

        private int SyncOrders(OdbcConnection odbcConn, SqliteConnection sqliteConn, SqliteTransaction tx, System.Text.StringBuilder log)
        {
            int count = 0;
            // Select all columns (*) to avoid strict column name mismatch errors with ODBC
            string query = "SELECT * FROM [ordbkup.DB]";

            using (var cmd = new OdbcCommand(query, odbcConn))
            using (var reader = cmd.ExecuteReader())
            {
                while (reader.Read())
                {
                    string orderNo = GetColumnString(reader, "OrderNo");
                    if (string.IsNullOrEmpty(orderNo)) continue;

                    using (var insertCmd = sqliteConn.CreateCommand())
                    {
                        insertCmd.Transaction = tx;
                        insertCmd.CommandText = @"
                            INSERT INTO StagingOrders (
                                OrderNo, Source, Time, AcDate, NoGuest, Price, Gst, Pst,
                                Disc_amt, Disc_per, Printed, Posted, Total, Serv, DiscType, Void, String1, OrderNo2
                            ) VALUES (@OrderNo, 'PARADOX', @Time, @AcDate, @NoGuest, @Price, @Gst, @Pst,
                                      @Disc_amt, @Disc_per, @Printed, @Posted, @Total, @Serv, @DiscType, @Void, @String1, @OrderNo2)
                            ON CONFLICT(OrderNo, Source) DO UPDATE SET
                                Time=excluded.Time, AcDate=excluded.AcDate, Total=excluded.Total,
                                Disc_amt=excluded.Disc_amt, Void=excluded.Void;";

                        insertCmd.Parameters.AddWithValue("@OrderNo", orderNo);
                        insertCmd.Parameters.AddWithValue("@Time", GetColumnString(reader, "Time"));
                        insertCmd.Parameters.AddWithValue("@AcDate", NormalizeParadoxDate(GetColumnString(reader, "AcDate")));
                        insertCmd.Parameters.AddWithValue("@NoGuest", GetColumnInt(reader, "NoGuest"));
                        insertCmd.Parameters.AddWithValue("@Price", GetColumnDouble(reader, "Price"));
                        insertCmd.Parameters.AddWithValue("@Gst", GetColumnDouble(reader, "GST"));
                        insertCmd.Parameters.AddWithValue("@Pst", GetColumnDouble(reader, "PST"));
                        insertCmd.Parameters.AddWithValue("@Disc_amt", GetColumnDouble(reader, "Disc_amt"));
                        insertCmd.Parameters.AddWithValue("@Disc_per", GetColumnDouble(reader, "Disc_per"));
                        insertCmd.Parameters.AddWithValue("@Printed", GetColumnString(reader, "Printed"));
                        insertCmd.Parameters.AddWithValue("@Posted", GetColumnString(reader, "Posted"));
                        insertCmd.Parameters.AddWithValue("@Total", GetColumnDouble(reader, "Total"));
                        insertCmd.Parameters.AddWithValue("@Serv", GetColumnDouble(reader, "Serv"));
                        insertCmd.Parameters.AddWithValue("@DiscType", GetColumnString(reader, "DiscType"));
                        insertCmd.Parameters.AddWithValue("@Void", GetColumnString(reader, "Void", "0"));
                        insertCmd.Parameters.AddWithValue("@String1", GetColumnString(reader, "String1"));
                        insertCmd.Parameters.AddWithValue("@OrderNo2", GetColumnString(reader, "OrderNo2"));

                        insertCmd.ExecuteNonQuery();
                        count++;
                    }
                }
            }
            return count;
        }

        private string NormalizeParadoxDate(string rawDate)
        {
            if (string.IsNullOrWhiteSpace(rawDate)) return rawDate;
            if (DateTime.TryParse(rawDate, out DateTime dt))
            {
                return dt.ToString("yyyy-MM-dd HH:mm:ss");
            }
            return rawDate;
        }

        private int SyncItems(OdbcConnection odbcConn, SqliteConnection sqliteConn, SqliteTransaction tx, System.Text.StringBuilder log)
        {
            int count = 0;
            string query = "SELECT * FROM [itembkup.DB]";

            using (var cmd = new OdbcCommand(query, odbcConn))
            using (var reader = cmd.ExecuteReader())
            {
                while (reader.Read())
                {
                    string orderNo = GetColumnString(reader, "OrderNo");
                    if (string.IsNullOrEmpty(orderNo)) continue;

                    using (var insertCmd = sqliteConn.CreateCommand())
                    {
                        insertCmd.Transaction = tx;
                        insertCmd.CommandText = @"
                            INSERT INTO StagingItems (
                                OrderNo, Source, MenuKey, Status, MenuNo, ItemNo, Description, Qty, Size, PriceBefDisc, DiscValue, Discount, DiscCode, DiscName
                            ) VALUES (@OrderNo, 'PARADOX', @MenuKey, @Status, @MenuNo, @ItemNo, @Description, @Qty, @Size, @PriceBefDisc, @DiscValue, @Discount, @DiscCode, @DiscName);";

                        insertCmd.Parameters.AddWithValue("@OrderNo", orderNo);
                        insertCmd.Parameters.AddWithValue("@MenuKey", GetColumnString(reader, "MenuKey"));
                        insertCmd.Parameters.AddWithValue("@Status", GetColumnString(reader, "Status"));
                        insertCmd.Parameters.AddWithValue("@MenuNo", GetColumnString(reader, "MenuNo"));
                        insertCmd.Parameters.AddWithValue("@ItemNo", GetColumnString(reader, "ItemNo"));
                        insertCmd.Parameters.AddWithValue("@Description", GetColumnString(reader, "Description"));
                        insertCmd.Parameters.AddWithValue("@Qty", GetColumnDouble(reader, "Qty", 1.0));
                        insertCmd.Parameters.AddWithValue("@Size", GetColumnString(reader, "Size"));
                        insertCmd.Parameters.AddWithValue("@PriceBefDisc", GetColumnDouble(reader, "PriceBefDisc"));
                        insertCmd.Parameters.AddWithValue("@DiscValue", GetColumnDouble(reader, "DiscValue"));
                        insertCmd.Parameters.AddWithValue("@Discount", GetColumnDouble(reader, "Discount"));
                        insertCmd.Parameters.AddWithValue("@DiscCode", GetColumnString(reader, "DiscCode"));
                        insertCmd.Parameters.AddWithValue("@DiscName", GetColumnString(reader, "DiscName"));

                        insertCmd.ExecuteNonQuery();
                        count++;
                    }
                }
            }
            return count;
        }

        private int SyncPayments(OdbcConnection odbcConn, SqliteConnection sqliteConn, SqliteTransaction tx, System.Text.StringBuilder log)
        {
            int count = 0;
            string query = "SELECT * FROM [ORDPAYBK.DB]";

            using (var cmd = new OdbcCommand(query, odbcConn))
            using (var reader = cmd.ExecuteReader())
            {
                while (reader.Read())
                {
                    string orderNo = GetColumnString(reader, "OrderNo");
                    if (string.IsNullOrEmpty(orderNo)) continue;

                    using (var insertCmd = sqliteConn.CreateCommand())
                    {
                        insertCmd.Transaction = tx;
                        insertCmd.CommandText = @"
                            INSERT INTO StagingPayments (
                                OrderNo, Source, SeqNo, PayID, PayName, Amount, OrgAmount, ExRate, PayDT, Change, PayName2
                            ) VALUES (@OrderNo, 'PARADOX', @SeqNo, @PayID, @PayName, @Amount, @OrgAmount, @ExRate, @PayDT, @Change, @PayName2);";

                        insertCmd.Parameters.AddWithValue("@OrderNo", orderNo);
                        insertCmd.Parameters.AddWithValue("@SeqNo", GetColumnInt(reader, "SeqNo"));
                        insertCmd.Parameters.AddWithValue("@PayID", GetColumnString(reader, "PayID"));
                        insertCmd.Parameters.AddWithValue("@PayName", GetColumnString(reader, "PayName"));
                        insertCmd.Parameters.AddWithValue("@Amount", GetColumnDouble(reader, "Amount"));
                        insertCmd.Parameters.AddWithValue("@OrgAmount", GetColumnDouble(reader, "OrgAmount"));
                        insertCmd.Parameters.AddWithValue("@ExRate", GetColumnDouble(reader, "ExRate", 1.0));
                        insertCmd.Parameters.AddWithValue("@PayDT", GetColumnString(reader, "PayDT"));
                        insertCmd.Parameters.AddWithValue("@Change", GetColumnDouble(reader, "Change"));
                        insertCmd.Parameters.AddWithValue("@PayName2", GetColumnString(reader, "PayName2"));

                        insertCmd.ExecuteNonQuery();
                        count++;
                    }
                }
            }
            return count;
        }

        // --- Safe Helper Methods for ODBC Reader ---

        private string GetColumnString(IDataRecord reader, string columnName, string defaultValue = "")
        {
            try
            {
                int ordinal = reader.GetOrdinal(columnName);
                if (reader.IsDBNull(ordinal)) return defaultValue;
                return reader.GetValue(ordinal)?.ToString()?.Trim() ?? defaultValue;
            }
            catch
            {
                return defaultValue;
            }
        }

        private int GetColumnInt(IDataRecord reader, string columnName, int defaultValue = 0)
        {
            try
            {
                int ordinal = reader.GetOrdinal(columnName);
                if (reader.IsDBNull(ordinal)) return defaultValue;
                return Convert.ToInt32(reader.GetValue(ordinal));
            }
            catch
            {
                return defaultValue;
            }
        }

        private double GetColumnDouble(IDataRecord reader, string columnName, double defaultValue = 0.0)
        {
            try
            {
                int ordinal = reader.GetOrdinal(columnName);
                if (reader.IsDBNull(ordinal)) return defaultValue;
                return Convert.ToDouble(reader.GetValue(ordinal));
            }
            catch
            {
                return defaultValue;
            }
        }
    }
}