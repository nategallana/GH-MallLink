using GH_Mall_Linking.Forms;
using GH_Mall_Linking.Services;
using GH_Mall_Linking.Views;
using System;
using System.Windows.Forms;

namespace GH_Mall_Linking
{
    internal static class Program
    {
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            // 1. Standard WinForms visual initialization
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // 2. Seed default configurations and create database schema
            try
            {
                DatabaseInitializer.Initialize();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"Failed to initialize local database:\n{ex.Message}",
                    "Database Initialization Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }

            // 3. Launch the Login Form
            Application.Run(new frmLogin());
        }
    }
}