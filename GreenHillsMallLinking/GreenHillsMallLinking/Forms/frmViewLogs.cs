using System;
using System.Data;
using System.Drawing;
using System.Windows.Forms;
using GH_Mall_Linking.Data;

namespace GH_Mall_Linking.Forms
{
    [System.ComponentModel.DesignerCategory("")]
    public partial class frmViewLogs : Form
    {
        private DataGridView gridLogs;
        private ComboBox cmbLevel;
        private Button btnRefresh;

        public frmViewLogs()
        {
            InitializeComponentProgrammatically();
            LoadLogs();
        }

        private void InitializeComponentProgrammatically()
        {
            this.Text = "System Logs";
            this.Size = new Size(850, 500);
            this.BackColor = Color.FromArgb(248, 249, 250);

            // Filter Header Panel
            Panel pnlTop = new Panel
            {
                Dock = DockStyle.Top,
                Height = 55,
                Padding = new Padding(15, 10, 15, 10)
            };

            Label lblLevel = new Label
            {
                Text = "Filter Level:",
                Location = new Point(15, 18),
                AutoSize = true,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };

            cmbLevel = new ComboBox
            {
                Location = new Point(95, 15),
                Width = 130,
                DropDownStyle = ComboBoxStyle.DropDownList
            };
            cmbLevel.Items.AddRange(new string[] { "All", "INFO", "WARNING", "ERROR", "DEBUG" });
            cmbLevel.SelectedIndex = 0;
            cmbLevel.SelectedIndexChanged += (s, e) => LoadLogs();

            btnRefresh = new Button
            {
                Text = "Refresh Logs",
                Location = new Point(235, 14),
                Width = 110,
                Height = 28,
                Cursor = Cursors.Hand
            };
            btnRefresh.Click += (s, e) => LoadLogs();

            pnlTop.Controls.Add(lblLevel);
            pnlTop.Controls.Add(cmbLevel);
            pnlTop.Controls.Add(btnRefresh);

            // Logs Grid
            gridLogs = new DataGridView
            {
                Dock = DockStyle.Fill,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
                AllowUserToAddRows = false,
                AllowUserToDeleteRows = false,
                ReadOnly = true,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                BackgroundColor = Color.White,
                BorderStyle = BorderStyle.None
            };

            Panel pnlGridContainer = new Panel
            {
                Dock = DockStyle.Fill,
                Padding = new Padding(15, 0, 15, 15)
            };
            pnlGridContainer.Controls.Add(gridLogs);

            this.Controls.Add(pnlGridContainer);
            this.Controls.Add(pnlTop);
        }

        private void LoadLogs()
        {
            try
            {
                string selectedLevel = cmbLevel.SelectedItem?.ToString() ?? "All";
                using (var db = new AppDbContext())
                {
                    var logsQuery = db.Logs.AsQueryable();
                    if (selectedLevel != "All")
                    {
                        logsQuery = logsQuery.Where(l => l.Level == selectedLevel);
                    }

                    var logsList = logsQuery.OrderByDescending(l => l.Timestamp).Take(500).ToList();
                    gridLogs.DataSource = logsList;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to load logs: {ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}