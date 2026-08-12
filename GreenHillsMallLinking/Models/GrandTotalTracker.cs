using System;
using System.ComponentModel.DataAnnotations;

namespace GH_Mall_Linking.Models
{
    public class GrandTotalTracker
    {
        [Key]
        public int Id { get; set; }

        public DateTime TargetDate { get; set; }

        public decimal OldGrandTotal { get; set; }

        public decimal NewGrandTotal { get; set; }

        public decimal DayGrossSales { get; set; }

        public int PreviousZCount { get; set; }

        public int NewZCount { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.Now;
    }
}