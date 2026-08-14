using System;
using System.Drawing;
using System.Windows.Forms;

namespace GH_Mall_Linking.Forms
{
    public partial class frmDashboardHome : Form
    {
        public frmDashboardHome()
        {
            InitializeComponentProgrammatically();
        }

        // Composite double-buffering keeps the sidebar sliding butter-smooth
        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ExStyle |= 0x02000000; // WS_EX_COMPOSITED
                return cp;
            }
        }

        private void InitializeComponentProgrammatically()
        {

            this.BackColor = Color.Lime;

            this.BackColor = Color.FromArgb(248, 249, 250);

            // Static Scrollable Container Panel (No Resize Events)
            Panel container = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                Padding = new Padding(20)
            };

            // Home Icon PictureBox
            PictureBox picHome = new PictureBox
            {
                Size = new Size(24, 24),
                Location = new Point(20, 15),
                SizeMode = PictureBoxSizeMode.Zoom,
                Cursor = Cursors.Hand,
                // Draws a simple Vector/GDI+ Home Icon directly so no external resources/images are needed
                Image = CreateHomeIconImage(24, 24, Color.Black)
            };

            // Home Icon Click Handler
            picHome.Click += (s, e) =>
            {
                // Reset scroll back to top when clicked
                container.AutoScrollPosition = new Point(0, 0);
            };

            // Main Title (shifted down and right to sit cleanly next to/below the home icon)
            Label lblTitle = new Label
            {
                Text = "GH MALL LINKING SYSTEM",
                Font = new Font("Century Gothic", 14f, FontStyle.Bold),
                ForeColor = Color.Black,
                Location = new Point(50, 15),
                AutoSize = true
            };

            // Subtitle
            Label lblSubtitle = new Label
            {
                Text = "User Manual & Quick Operational Guide",
                Font = new Font("Century Gothic", 9.5f, FontStyle.Italic),
                ForeColor = Color.Black,
                Location = new Point(50, 43),
                AutoSize = true
            };

            // Main Manual Content
            Label lblContent = new Label
            {
                Text =
                    "1. PROCESS EOD\n" +
                    "• Used to run End-of-Day data processing.\n" +
                    "• Select your Start/End Date, check options, and run live processing.\n" +
                    "• Real-time logs and error reports stream directly in the console.\n\n" +

                    "2. PAYMENT METHODS\n" +
                    "• Map store payment types (Cash, Card, E-Wallets) to mall requirements.\n\n" +

                    "3. SYSTEM SETTINGS\n" +
                    "• Configure source data paths, Python executable locations, and database connections.\n\n" +
                   
                    "4. HOME PAGE\n" +
                    "• Access the main dashboard and overview of the system.\n\n" +

                    "5. EXIT\n" +
                    "• Close the application and save any unsaved changes.\n",

                Font = new Font("Century Gothic", 9.5f, FontStyle.Regular),
                ForeColor = Color.Black,
                Location = new Point(20, 85),
                Size = new Size(580, 420),
                AutoSize = false // Fixed size prevents WinForms layout engine triggers
            };

            container.Controls.Add(picHome);
            container.Controls.Add(lblTitle);
            container.Controls.Add(lblSubtitle);
            container.Controls.Add(lblContent);

            this.Controls.Add(container);
        }

        // Helper method to dynamically generate a clean Home icon bitmap
        private Bitmap CreateHomeIconImage(int width, int height, Color color)
        {
            Bitmap bmp = new Bitmap(width, height);
            using (Graphics g = Graphics.FromImage(bmp))
            {
                g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
                using (Pen pen = new Pen(color, 2f))
                {
                    // Roof
                    g.DrawLines(pen, new Point[] {
                        new Point(2, 11),
                        new Point(12, 3),
                        new Point(22, 11)
                    });

                    // House body
                    g.DrawRectangle(pen, 5, 11, 14, 10);

                    // Door
                    g.DrawRectangle(pen, 10, 15, 4, 6);
                }
            }
            return bmp;
        }
    }
}