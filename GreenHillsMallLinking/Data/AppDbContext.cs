using GH_Mall_Linking.Models;
using GHMallLinking.Models;
using Microsoft.EntityFrameworkCore;
using System;
using System.IO;

namespace GH_Mall_Linking.Data
{
    public class AppDbContext : DbContext
    {
        public DbSet<Configuration> Configurations { get; set; }
        public DbSet<Log> Logs { get; set; }
        public DbSet<SyncHistory> SyncHistories { get; set; }
        public DbSet<PaymentMethod> PaymentMethods { get; set; }
        public DbSet<PaymentMethodKeyword> PaymentMethodKeywords { get; set; }
        public DbSet<GrandTotalTracker> GrandTotalTrackers { get; set; }
        public DbSet<SalesLine> SalesLines { get; set; }

        // --- NEW UNIFIED SYSTEM MODELS ---
        public DbSet<EodTransaction> EodTransactions { get; set; }
        public DbSet<PaymentMapping> PaymentMappings { get; set; }

        protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        {
            if (!optionsBuilder.IsConfigured)
            {
                // Ensures EF Core and PythonBridge both access the exact same DB file
                string dbPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gh_mall_linking.db");
                optionsBuilder.UseSqlite($"Data Source={dbPath}");
            }
        }

        protected override void OnModelCreating(ModelBuilder modelBuilder)
        {
            base.OnModelCreating(modelBuilder);
        }
    }
}