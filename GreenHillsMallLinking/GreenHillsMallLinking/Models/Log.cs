using System;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GH_Mall_Linking.Models
{
    public class Log
    {
        [Key]
        [DatabaseGenerated(DatabaseGeneratedOption.Identity)]
        public int Id { get; set; }

        public DateTime Timestamp { get; set; } = DateTime.Now;

        [Required]
        public string Level { get; set; } = "INFO";

        [Required]
        public string Message { get; set; } = string.Empty;

        [Required]
        public string Source { get; set; } = "General"; // Prevents NOT NULL constraint failure in SQLite
    }
}