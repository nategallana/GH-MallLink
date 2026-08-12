using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;
using System;
using System.Linq;

namespace GH_Mall_Linking.Services
{
    public class PaymentMethodResolver
    {
        /// <summary>
        /// Resolves an incoming raw payment type from Paradox/Cloud XML.
        /// If unknown, automatically inserts a new row in PaymentMethods.
        /// </summary>
        public static PaymentMethod GetOrAddPaymentMethod(string rawPaymentName)
        {
            if (string.IsNullOrWhiteSpace(rawPaymentName))
                rawPaymentName = "UNKNOWN";

            string cleanedName = rawPaymentName.Trim().ToUpper();

            using (var context = new AppDbContext())
            {
                // 1. Exact match check
                var existing = context.PaymentMethods
                    .FirstOrDefault(p => p.MethodName.ToUpper() == cleanedName);

                if (existing != null)
                {
                    return existing;
                }

                // 2. Keyword match check
                var keywordMatch = context.PaymentMethodKeywords
                    .Where(k => cleanedName.Contains(k.Keyword.ToUpper()))
                    .Select(k => k.PaymentMethod)
                    .FirstOrDefault();

                if (keywordMatch != null)
                {
                    return keywordMatch;
                }

                // 3. AUTO-REGISTER: Create new payment method if unrecognized
                var newPaymentMethod = new PaymentMethod
                {
                    MethodName = cleanedName,
                    GhCode = "99", // Unmapped temporary code
                    IsDefault = false,
                    IsActive = true,
                    CreatedAt = DateTime.Now
                };

                context.PaymentMethods.Add(newPaymentMethod);
                context.SaveChanges();

                // Add exact keyword for fast subsequent hits
                context.PaymentMethodKeywords.Add(new PaymentMethodKeyword
                {
                    PaymentMethodId = newPaymentMethod.Id,
                    Keyword = cleanedName
                });
                context.SaveChanges();

                return newPaymentMethod;
            }
        }
    }
}