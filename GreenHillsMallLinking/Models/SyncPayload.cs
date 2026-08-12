using System;
using System.Collections.Generic;

namespace GHMallLinking.Models
{
    public class SyncRequest
    {
        public string Action { get; set; } // e.g., "PROCESS_EOD", "SYNC_ONLY"
        public DateTime TargetDate { get; set; }
        public List<EodTransaction> Transactions { get; set; } = new List<EodTransaction>();
    }

    public class SyncResult
    {
        public bool IsSuccess { get; set; }
        public string Message { get; set; } 
        public int ProcessedRecords { get; set; }
        public DateTime ProcessedAt { get; set; } = DateTime.Now;
        public string ErrorDetails { get; set; }
    }
}