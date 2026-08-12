namespace GHMallLinking.Models
{
    public class PaymentMapping
    {
        public int Id { get; set; }
        public string LocalPaymentCode { get; set; }  // e.g., "GCASH", "VISA"
        public string MallPaymentCode { get; set; }   // e.g., "MALL_EWALLET_01"
        public string PaymentDescription { get; set; }
        public bool IsActive { get; set; } = true;
    }
}