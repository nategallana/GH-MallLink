using GH_Mall_Linking.Data;
using GH_Mall_Linking.Services;
using GH_Mall_Linking.Forms;
using System;
using System.Drawing;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace GH_Mall_Linking.Forms
{
    public partial class frmDashboardOverview : Form
    {
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern bool ReleaseCapture();

        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);

        private const int WM_NCLBUTTONDOWN = 0xA1;
        private const int HT_CAPTION = 0x2;

        private const int RailWidth = 55;
        private Form _activeForm = null;

        // --- PURE CODE-BEHIND CONTROL DECLARATIONS ---
        private Panel panelSidebar;
        private Button btnHome;
        private Button btnProcessEOD;
        private Button btnPaymentMethods;
        private Button btnSettings;
        private Button btnViewLogs;
        private Button btnExit;

        public void OpenChildForm(Form childForm)
        {
            if (_activeForm != null)
            {
                _activeForm.Close();
                _activeForm.Dispose();
            }

            _activeForm = childForm;
            childForm.TopLevel = false;
            childForm.FormBorderStyle = FormBorderStyle.None;
            childForm.AutoSize = false;
            childForm.Dock = DockStyle.Fill;

            mainPanel.Controls.Clear();
            mainPanel.Controls.Add(childForm);
            mainPanel.Tag = childForm;

            childForm.Show();
            if (panelSidebar != null)
            {
                panelSidebar.BringToFront();
            }
        }

        /// <summary>
        /// Enables/disables every sidebar navigation button. Any child form doing a
        /// long-running operation (Process EOD, Settings save) should call this with
        /// false before starting and true when done, so the user can't navigate away
        /// or trigger another operation mid-run. Call via:
        ///   (this.ParentForm as frmDashboardOverview)?.SetSidebarEnabled(false);
        /// from inside a form opened through OpenChildForm — ParentForm resolves up
        /// through mainPanel to this shell since the child form is embedded, not a
        /// separate top-level window.
        /// </summary>
        public void SetSidebarEnabled(bool enabled)
        {
            if (btnHome != null) btnHome.Enabled = enabled;
            if (btnProcessEOD != null) btnProcessEOD.Enabled = enabled;
            if (btnPaymentMethods != null) btnPaymentMethods.Enabled = enabled;
            if (btnSettings != null) btnSettings.Enabled = enabled;
            if (btnViewLogs != null) btnViewLogs.Enabled = enabled;
            if (btnExit != null) btnExit.Enabled = enabled;
        }

        public frmDashboardOverview()
        {
            InitializeComponent();

            InitializeCustomSidebar();
            ApplyDarkRailStyling();
            SetupTooltips();
            RegisterButtonEvents();
            AdjustMainPanelLayout();

            this.SetStyle(ControlStyles.AllPaintingInWmPaint |
                   ControlStyles.UserPaint |
                   ControlStyles.DoubleBuffer |
                   ControlStyles.OptimizedDoubleBuffer, true);
            this.UpdateStyles();

            // FIX: was called directly here, in the constructor — but at this point
            // frmDashboardOverview has no window handle yet (frmLogin only calls
            // .Show() AFTER the constructor returns), and Dock/layout calculations
            // performed before a control has a real handle don't reliably take effect.
            // Every later navigation works because it happens after the form is
            // already live. Load fires right as the form is actually about to
            // display, once a handle genuinely exists.
            this.Load += (s, e) => OpenChildForm(new frmDashboardHome());
        }

        private void InitializeCustomSidebar()
        {
            panelSidebar = new Panel
            {
                Name = "panelSidebar",
                Dock = DockStyle.Left,
                Width = RailWidth,
                BackColor = Color.FromArgb(40, 40, 40)
            };

            btnHome = new Button { Name = "btnHome", Text = "🏠" };
            btnProcessEOD = new Button { Name = "btnProcessEOD", Text = "📊" };
            btnPaymentMethods = new Button { Name = "btnPaymentMethods", Text = "💳" };
            btnSettings = new Button { Name = "btnSettings", Text = "⚙️" };
            btnViewLogs = new Button { Name = "btnViewLogs", Text = "📋" };
            btnExit = new Button { Name = "btnExit", Text = "🚪" };

            panelSidebar.Controls.Add(btnHome);
            panelSidebar.Controls.Add(btnProcessEOD);
            panelSidebar.Controls.Add(btnPaymentMethods);
            panelSidebar.Controls.Add(btnSettings);
            panelSidebar.Controls.Add(btnViewLogs);
            panelSidebar.Controls.Add(btnExit);

            this.Controls.Add(panelSidebar);
            panelSidebar.BringToFront();
        }

        private void DragForm(MouseEventArgs e)
        {
            if (e.Button == MouseButtons.Left)
            {
                ReleaseCapture();
                SendMessage(Handle, WM_NCLBUTTONDOWN, HT_CAPTION, 0);
            }
        }

        #region Custom UI Styling & Tooltips
        private void ApplyDarkRailStyling()
        {
            this.BackColor = Color.FromArgb(0, 0, 0);

            if (panelHeader != null)
            {
                panelHeader.MouseDown += (s, e) => DragForm(e);
            }

            if (headerLabel != null)
            {
                headerLabel.Cursor = Cursors.Default;
                headerLabel.MouseDown += (s, e) => DragForm(e);
            }

            if (mainPanel != null)
            {
                mainPanel.Region = null;
            }

            Button[] sidebarButtons = {
                btnHome, btnProcessEOD, btnPaymentMethods,
                btnSettings, btnViewLogs, btnExit
            };

            int topOffset = 15;
            int buttonGap = 50;

            for (int i = 0; i < sidebarButtons.Length; i++)
            {
                var btn = sidebarButtons[i];
                if (btn == null) continue;

                btn.FlatStyle = FlatStyle.Flat;
                btn.FlatAppearance.BorderSize = 0;
                btn.BackColor = Color.Transparent;
                btn.ForeColor = Color.White;
                btn.Font = new Font("Segoe UI Emoji", 14F, FontStyle.Regular);
                btn.Cursor = Cursors.Hand;

                btn.Size = new Size(45, 45);
                btn.Location = new Point(5, topOffset + (i * buttonGap));

                btn.MouseEnter += (s, e) => { if (btn.Enabled) btn.BackColor = Color.FromArgb(60, 60, 60); };
                btn.MouseLeave += (s, e) => { btn.BackColor = Color.Transparent; };
            }
        }

        private void SetupTooltips()
        {
            ToolTip toolTip = new ToolTip
            {
                AutoPopDelay = 5000,
                InitialDelay = 200,
                ReshowDelay = 100,
                ShowAlways = true
            };

            if (btnHome != null) toolTip.SetToolTip(btnHome, "Home / Manual");
            if (btnProcessEOD != null) toolTip.SetToolTip(btnProcessEOD, "Process EOD");
            if (btnPaymentMethods != null) toolTip.SetToolTip(btnPaymentMethods, "Payment Methods");
            if (btnSettings != null) toolTip.SetToolTip(btnSettings, "Settings");
            if (btnViewLogs != null) toolTip.SetToolTip(btnViewLogs, "View Logs");
            if (btnExit != null) toolTip.SetToolTip(btnExit, "Exit");
        }

        private void AdjustMainPanelLayout()
        {
            if (mainPanel != null && panelSidebar != null)
            {
                int leftMargin = 0;
                mainPanel.Left = panelSidebar.Width + leftMargin;
                mainPanel.Width = this.ClientSize.Width - mainPanel.Left;
            }
        }
        #endregion

        #region Navigation Registration
        private void RegisterButtonEvents()
        {
            if (btnHome != null)
                btnHome.Click += (s, e) => OpenChildForm(new frmDashboardHome());

            if (btnProcessEOD != null)
                btnProcessEOD.Click += (s, e) => OpenChildForm(new frmProcessEOD());

            if (btnPaymentMethods != null)
                btnPaymentMethods.Click += (s, e) => OpenChildForm(new frmPaymentMethods());

            if (btnSettings != null)
                btnSettings.Click += (s, e) => OpenChildForm(new frmSettings());

            if (btnViewLogs != null)
                btnViewLogs.Click += (s, e) => OpenChildForm(new frmViewLogs());

            if (btnExit != null)
                btnExit.Click += (s, e) => Application.Exit();
        }
        #endregion

        #region Auto-generated Designer Event Stubs
        private void panelHeader_Paint(object sender, PaintEventArgs e) { }
        private void label1_Click(object sender, EventArgs e) { }
        private void label2_Click(object sender, EventArgs e) { }
        private void mainPanel_Paint(object sender, PaintEventArgs e) { }
        private void textBox1_TextChanged(object sender, EventArgs e) { }
        #endregion
    }
}