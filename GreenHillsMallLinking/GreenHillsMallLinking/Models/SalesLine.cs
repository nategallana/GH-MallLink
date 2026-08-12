//SalesLine,cs
using System;
using System.ComponentModel.DataAnnotations;

namespace GH_Mall_Linking.Models
{
    public class SalesLine
    {
        [Key]
        public int Id { get; set; }

        public int EodRunId { get; set; }

        public string LineCode { get; set; } // "01"=Hourly, "99"=Daily Totals, "95"=Grand Totals

        public string SalesTime { get; set; }

        public string PosCode { get; set; }

        public DateTime SalesDate { get; set; }

        public string TerminalNo { get; set; }

        public decimal GrossSales { get; set; }

        public decimal VatableSales { get; set; }

        public decimal VatAmount { get; set; }

        public decimal NetSales { get; set; }

        public string FormattedFixedString { get; set; }
    }
}