using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace GH_Mall_Linking.Models
{
    public class PaymentMethodKeyword
    {
        [Key]
        public int Id { get; set; }

        public int PaymentMethodId { get; set; }

        [Required]
        public string Keyword { get; set; } // Pattern string matched from Paradox String1

        [ForeignKey("PaymentMethodId")]
        public virtual PaymentMethod PaymentMethod { get; set; }
    }
}