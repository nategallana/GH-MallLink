using System.Collections.Generic;
using System.Linq;
using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;

namespace GH_Mall_Linking.Services
{
    public class ConfigService
    {
        // Fetch a configuration setting by key (e.g., "MallName", "FtpHost")
        public string GetValue(string key, string defaultValue = "")
        {
            using (var db = new AppDbContext())
            {
                var config = db.Configurations.FirstOrDefault(c => c.Key == key);
                return config != null ? config.Value : defaultValue;
            }
        }

        // Save or update a single configuration key/value pair
        public void SetValue(string key, string value)
        {
            using (var db = new AppDbContext())
            {
                var config = db.Configurations.FirstOrDefault(c => c.Key == key);

                if (config == null)
                {
                    db.Configurations.Add(new Configuration
                    {
                        Key = key,
                        Value = value
                    });
                }
                else
                {
                    config.Value = value;
                }

                db.SaveChanges();
            }
        }

        /// <summary>
        /// Saves multiple key/value pairs in ONE connection and ONE SaveChanges call,
        /// instead of one round-trip per key. Use this for anything saving more than a
        /// couple of settings at once (e.g. a Settings form's Save button) — a dozen
        /// individual SetValue() calls means a dozen separate SQLite connections and
        /// transactions for a single user action, which is the slow path.
        /// </summary>
        public void SetValues(Dictionary<string, string> values)
        {
            if (values == null || values.Count == 0) return;

            using (var db = new AppDbContext())
            {
                var keys = values.Keys.ToList();
                var existing = db.Configurations
                    .Where(c => keys.Contains(c.Key))
                    .ToDictionary(c => c.Key, c => c);

                foreach (var kvp in values)
                {
                    if (existing.TryGetValue(kvp.Key, out var config))
                    {
                        config.Value = kvp.Value;
                    }
                    else
                    {
                        db.Configurations.Add(new Configuration
                        {
                            Key = kvp.Key,
                            Value = kvp.Value
                        });
                    }
                }

                db.SaveChanges();
            }
        }

        // Get all key-value settings as a Dictionary for forms like frmSettings
        public Dictionary<string, string> GetAll()
        {
            using (var db = new AppDbContext())
            {
                return db.Configurations.ToDictionary(c => c.Key, c => c.Value);
            }
        }
    }
}