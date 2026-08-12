using System;
using System.Data;
using System.Data.SQLite;
using System.IO;
namespace GH_Mall_Linking.Data

{
    public class DatabaseHelper
    {
        private readonly string _connectionString;

        public DatabaseHelper()
        {
            string basePath = AppDomain.CurrentDomain.BaseDirectory;

            // Standardized to match EF Core's SQLite filename
            string dbPath = Path.Combine(basePath, "gh_mall_linking.db");

            _connectionString = $"Data Source={dbPath};Version=3;";
        }

        public SQLiteConnection GetConnection()
        {
            return new SQLiteConnection(_connectionString);
        }

        public DataTable ExecuteQuery(string query, SQLiteParameter[] parameters = null)
        {
            using (var conn = GetConnection())
            using (var cmd = new SQLiteCommand(query, conn))
            {
                if (parameters != null)
                {
                    cmd.Parameters.AddRange(parameters);
                }

                using (var adapter = new SQLiteDataAdapter(cmd))
                {
                    DataTable dt = new DataTable();
                    adapter.Fill(dt);
                    return dt;
                }
            }
        }

        public int ExecuteNonQuery(string query, SQLiteParameter[] parameters = null)
        {
            using (var conn = GetConnection())
            using (var cmd = new SQLiteCommand(query, conn))
            {
                if (parameters != null)
                {
                    cmd.Parameters.AddRange(parameters);
                }

                conn.Open();
                return cmd.ExecuteNonQuery();
            }
        }
    }
}

