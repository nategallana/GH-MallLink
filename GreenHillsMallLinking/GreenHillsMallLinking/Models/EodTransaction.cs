//EodTransaction.cs
using System;

namespace GHMallLinking.Models
{
    public class EodTransaction
    {
        public int Id { get; set; }
        public string StoreCode { get; set; }
        public string MallName { get; set; }
        public DateTime TransactionDate { get; set; }
        public decimal GrossSales { get; set; }
        public decimal NetSales { get; set; }
        public decimal TotalDiscount { get; set; }
        public decimal TotalVat { get; set; }
        public int TransactionCount { get; set; }
        public string Status { get; set; } // Pending, Synced, Failed
        public DateTime CreatedAt { get; set; } = DateTime.Now;
    }
}