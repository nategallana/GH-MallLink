namespace GH_Mall_Linking.Constants
{
    public static class ParadoxQueries
    {
        // Database Password Constant
        public const string DB_PASSWORD = "5A*281";

        // Active Table Queries
        public const string OrdersQuery = "SELECT * FROM [Orders]";
        public const string OrdItemQuery = "SELECT * FROM [OrdItem]";
        public const string OrdPayQuery = "SELECT * FROM [OrdPay]";

        // Backup Table Queries
        public const string OkupQuery = "SELECT * FROM [Ordbkup]";
        public const string ItemBkupQuery = "SELECT * FROM [itembkup]";
        public const string OrdPayBkQuery = "SELECT * FROM [OrdPayBK]";
    }
}