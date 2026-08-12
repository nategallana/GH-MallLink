using GH_Mall_Linking.Services;
using GH_Mall_Linking.Forms;
using System;
using System.Drawing;
using System.Windows.Forms;

namespace GH_Mall_Linking.Views
{
    public partial class frmLogin : Form
    {
        private readonly ConfigService _configService;

        private Label lblPassword;
        private TextBox txtPassword;
        private Button btnLogin;

        public frmLogin()
        {
            _configService = new ConfigService();
            InitializeComponentProgrammatically();
        }

        private void InitializeComponentProgrammatically()
        {
            this.Text = "Login";
            this.Size = new Size(320, 180);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;

            lblPassword = new Label { Text = "Password:", Location = new Point(20, 30), AutoSize = true };
            txtPassword = new TextBox { Location = new Point(100, 28), Width = 170, PasswordChar = '*' };

            btnLogin = new Button { Text = "Login", Location = new Point(100, 70), Width = 100, Height = 30 };
            btnLogin.Click += BtnLogin_Click;

            this.Controls.Add(lblPassword);
            this.Controls.Add(txtPassword);
            this.Controls.Add(btnLogin);

            this.AcceptButton = btnLogin; // Pressing Enter triggers Login
        }

        private void BtnLogin_Click(object sender, EventArgs e)
        {
            // FIX: was a hardcoded literal ("nate") that never referenced the stored
            // Configuration password at all — meaning changing the password via
            // Settings had zero effect on what actually let you log in. Now reads the
            // real stored value (defaults to "Admin" to match the seeded default).
            string storedPassword = _configService.GetValue("Password", "Admin");

            if (txtPassword.Text == storedPassword)
            {
                // 1. Instantiate the dashboard form
                frmDashboardOverview dashboard = new frmDashboardOverview();

                // 2. Ensure closing the dashboard fully exits the application
                dashboard.FormClosed += (s, args) => this.Close();

                // 3. Show the dashboard
                dashboard.Show();

                // 4. Hide the login form
                this.Hide();
            }
            else
            {
                MessageBox.Show("Invalid Password!", "Access Denied", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}