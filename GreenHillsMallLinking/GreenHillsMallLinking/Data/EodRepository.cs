using System;
using System.Collections.Generic;
using System.Data;
using System.Data.SQLite; 
using GHMallLinking.Models;
using GH_Mall_Linking.Services;
using GH_Mall_Linking.Data;

namespace GHMallLinking.Data
{
    public class EodRepository
    {
        private readonly DatabaseHelper _dbHelper;

        public EodRepository()
        {
            _dbHelper = new DatabaseHelper();
        }

        // Fetch pending EOD transactions by date
        public List<EodTransaction> GetPendingEodTransactions(DateTime date)
        {
            List<EodTransaction> list = new List<EodTransaction>();

            // SQLite uses strftime for date casting/formatting
            string query = "SELECT * FROM EodTransactions WHERE strftime('%Y-%m-%d', TransactionDate) = @Date AND Status = 'Pending'";

            SQLiteParameter[] parameters = {
                new SQLiteParameter("@Date", date.ToString("yyyy-MM-dd"))
            };

            DataTable dt = _dbHelper.ExecuteQuery(query, parameters);

            foreach (DataRow row in dt.Rows)
            {
                list.Add(new EodTransaction
                {
                    Id = Convert.ToInt32(row["Id"]),
                    StoreCode = row["StoreCode"].ToString(),
                    MallName = row["MallName"].ToString(),
                    TransactionDate = Convert.ToDateTime(row["TransactionDate"]),
                    GrossSales = Convert.ToDecimal(row["GrossSales"]),
                    NetSales = Convert.ToDecimal(row["NetSales"]),
                    TotalDiscount = Convert.ToDecimal(row["TotalDiscount"]),
                    TotalVat = Convert.ToDecimal(row["TotalVat"]),
                    TransactionCount = Convert.ToInt32(row["TransactionCount"]),
                    Status = row["Status"].ToString()
                });
            }

            return list;
        }

        // Update status after Python engine sync
        public bool UpdateTransactionStatus(int id, string status)
        {
            string query = "UPDATE EodTransactions SET Status = @Status WHERE Id = @Id";

            SQLiteParameter[] parameters = {
                new SQLiteParameter("@Status", status),
                new SQLiteParameter("@Id", id)
            };

            return _dbHelper.ExecuteNonQuery(query, parameters) > 0;
        }
    }
}