using GH_Mall_Linking.Services;
using System;
using System.Drawing;
using System.Windows.Forms;

namespace GH_Mall_Linking.Forms
{
    public partial class frmChangePassword : Form
    {
        private readonly ConfigService _configService;

        private Label lblCurrent;
        private TextBox txtCurrent;
        private Label lblNew;
        private TextBox txtNew;
        private Label lblConfirm;
        private TextBox txtConfirm;
        private Button btnSave;
        private Button btnCancel;

        public frmChangePassword()
        {
            _configService = new ConfigService();
            InitializeComponentProgrammatically();
        }

        private void InitializeComponentProgrammatically()
        {
            this.Text = "Change Password";
            this.Size = new Size(340, 230);
            this.StartPosition = FormStartPosition.CenterParent;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;

            lblCurrent = new Label { Text = "Current Password:", Location = new Point(20, 25), AutoSize = true };
            txtCurrent = new TextBox { Location = new Point(150, 22), Width = 150, PasswordChar = '*' };

            lblNew = new Label { Text = "New Password:", Location = new Point(20, 60), AutoSize = true };
            txtNew = new TextBox { Location = new Point(150, 57), Width = 150, PasswordChar = '*' };

            lblConfirm = new Label { Text = "Confirm New Password:", Location = new Point(20, 95), AutoSize = true };
            txtConfirm = new TextBox { Location = new Point(150, 92), Width = 150, PasswordChar = '*' };

            btnSave = new Button { Text = "Save", Location = new Point(60, 140), Width = 90, Height = 32 };
            btnSave.Click += BtnSave_Click;

            btnCancel = new Button { Text = "Cancel", Location = new Point(170, 140), Width = 90, Height = 32 };
            btnCancel.Click += (s, e) => this.Close();

            this.Controls.Add(lblCurrent);
            this.Controls.Add(txtCurrent);
            this.Controls.Add(lblNew);
            this.Controls.Add(txtNew);
            this.Controls.Add(lblConfirm);
            this.Controls.Add(txtConfirm);
            this.Controls.Add(btnSave);
            this.Controls.Add(btnCancel);

            this.AcceptButton = btnSave;
        }

        private void BtnSave_Click(object sender, EventArgs e)
        {
            string currentStored = _configService.GetValue("Password", "Admin");

            if (txtCurrent.Text != currentStored)
            {
                MessageBox.Show("Current password is incorrect.", "Validation Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtCurrent.Focus();
                return;
            }

            if (string.IsNullOrWhiteSpace(txtNew.Text))
            {
                MessageBox.Show("New password cannot be blank.", "Validation Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtNew.Focus();
                return;
            }

            if (txtNew.Text != txtConfirm.Text)
            {
                MessageBox.Show("New password and confirmation do not match.", "Validation Error", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtConfirm.Focus();
                return;
            }

            _configService.SetValue("Password", txtNew.Text);

            MessageBox.Show("Password changed successfully.", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
            this.Close();
        }
    }
}