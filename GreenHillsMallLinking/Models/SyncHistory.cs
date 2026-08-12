using System;
using System.ComponentModel.DataAnnotations;

namespace GH_Mall_Linking.Models
{
    public class SyncHistory
    {
        [Key]
        public int Id { get; set; }

        public DateTime StartedAt { get; set; } = DateTime.Now;

        public DateTime? CompletedAt { get; set; }

        public string Status { get; set; } = "Running";

        public int OrdersSynced { get; set; }

        public int ItemsSynced { get; set; }

        public string ErrorDetails { get; set; } = string.Empty;
    }
}