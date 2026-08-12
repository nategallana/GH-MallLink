using System;
using System.Drawing;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Forms;
using GH_Mall_Linking.Services;

namespace GH_Mall_Linking.Forms
{
    public partial class frmProcessEOD : Form
    {
        private Panel cardControlPanel;
        private Label lblStartDate;
        private Label lblEndDate;
        private DateTimePicker dtpStartDate;
        private DateTimePicker dtpEndDate;
        private CheckBox chkSyncParadox;
        private Button btnProcessEOD;

        // Data source selector (Paradox vs Cloud)
        private Label lblSource;
        private RadioButton rbSourceParadox;
        private RadioButton rbSourceCloud;

        private Panel statusContainer;
        private ProgressBar progressBar;
        private Label lblStatus;
        private RichTextBox txtLogOutput;

        private readonly PythonBridgeService _pythonBridge;
        private readonly SyncService _syncService;
        private readonly ConfigService _configService;
        private readonly LogService _logService;

        public frmProcessEOD()
        {
            InitializeComponentProgrammatically();
            _pythonBridge = new PythonBridgeService();
            _syncService = new SyncService();
            _configService = new ConfigService();
            _logService = new LogService();

            ApplySavedSourceSelection();
        }

        private void InitializeComponentProgrammatically()
        {
            this.BackColor = Color.FromArgb(248, 249, 250);
            this.Padding = new Padding(20);

            // 1. Top Card Container
            cardControlPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 155,
                BackColor = Color.White,
                Padding = new Padding(20)
            };

            cardControlPanel.Paint += (s, e) =>
            {
                ControlPaint.DrawBorder(
                    e.Graphics,
                    cardControlPanel.ClientRectangle,
                    Color.FromArgb(222, 226, 230),
                    ButtonBorderStyle.Solid
                );
            };

            // --- Start Date ---
            lblStartDate = new Label
            {
                Text = "Start Date",
                Location = new Point(20, 16),
                AutoSize = true,
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(70, 80, 95)
            };

            dtpStartDate = new DateTimePicker
            {
                Format = DateTimePickerFormat.Short,
                Location = new Point(20, 38),
                Width = 120,
                Font = new Font("Segoe UI", 9.5f),
                Value = DateTime.Today
            };

            // --- End Date ---
            lblEndDate = new Label
            {
                Text = "End Date",
                Location = new Point(155, 16),
                AutoSize = true,
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(70, 80, 95)
            };

            dtpEndDate = new DateTimePicker
            {
                Format = DateTimePickerFormat.Short,
                Location = new Point(155, 38),
                Width = 120,
                Font = new Font("Segoe UI", 9.5f),
                Value = DateTime.Today
            };

            // --- Checkbox Option ---
            chkSyncParadox = new CheckBox
            {
                Text = "Sync Paradox data first",
                Location = new Point(20, 76),
                AutoSize = true,
                Checked = true,
                Font = new Font("Segoe UI", 9f),
                ForeColor = Color.FromArgb(50, 50, 50),
                Cursor = Cursors.Hand
            };

            // --- Data Source Section ---
            lblSource = new Label
            {
                Text = "Data Source:",
                Location = new Point(20, 108),
                AutoSize = true,
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(70, 80, 95)
            };

            rbSourceParadox = new RadioButton
            {
                Text = "Paradox",
                Location = new Point(110, 106),
                AutoSize = true,
                Checked = true,
                Font = new Font("Segoe UI", 9f),
                ForeColor = Color.FromArgb(50, 50, 50),
                Cursor = Cursors.Hand
            };
            rbSourceParadox.CheckedChanged += SourceRadio_CheckedChanged;

            rbSourceCloud = new RadioButton
            {
                Text = "Cloud",
                Location = new Point(190, 106),
                AutoSize = true,
                Font = new Font("Segoe UI", 9f),
                ForeColor = Color.FromArgb(50, 50, 50),
                Cursor = Cursors.Hand
            };
            rbSourceCloud.CheckedChanged += SourceRadio_CheckedChanged;

            // --- Primary Action Button ---
            btnProcessEOD = new Button
            {
                Text = "▶  Process EOD",
                Size = new Size(145, 45),
                Location = new Point(cardControlPanel.Width - 165, 35),
                Anchor = AnchorStyles.Top | AnchorStyles.Right,
                BackColor = Color.FromArgb(13, 110, 253),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnProcessEOD.FlatAppearance.BorderSize = 0;
            btnProcessEOD.Click += BtnProcessEOD_Click;

            cardControlPanel.Resize += (s, e) =>
            {
                btnProcessEOD.Location = new Point(cardControlPanel.Width - 165, 38);
            };

            cardControlPanel.Controls.Add(lblStartDate);
            cardControlPanel.Controls.Add(dtpStartDate);
            cardControlPanel.Controls.Add(lblEndDate);
            cardControlPanel.Controls.Add(dtpEndDate);
            cardControlPanel.Controls.Add(chkSyncParadox);
            cardControlPanel.Controls.Add(lblSource);
            cardControlPanel.Controls.Add(rbSourceParadox);
            cardControlPanel.Controls.Add(rbSourceCloud);
            cardControlPanel.Controls.Add(btnProcessEOD);

            // 2. Status & Progress Section
            statusContainer = new Panel
            {
                Dock = DockStyle.Top,
                Height = 50,
                Padding = new Padding(0, 12, 0, 8),
                BackColor = Color.Transparent
            };

            progressBar = new ProgressBar
            {
                Dock = DockStyle.Top,
                Height = 6,
                Style = ProgressBarStyle.Blocks,
                Visible = true
            };

            lblStatus = new Label
            {
                Text = "Ready to process.",
                Dock = DockStyle.Bottom,
                Height = 22,
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                ForeColor = Color.FromArgb(108, 117, 125)
            };

            statusContainer.Controls.Add(lblStatus);
            statusContainer.Controls.Add(progressBar);

            // 3. Log Console Terminal
            txtLogOutput = new RichTextBox
            {
                Dock = DockStyle.Fill,
                ReadOnly = true,
                BackColor = Color.FromArgb(24, 28, 36),
                ForeColor = Color.FromArgb(220, 224, 230),
                Font = new Font("Consolas", 9.5f),
                BorderStyle = BorderStyle.None,
                Padding = new Padding(10)
            };

            this.Controls.Add(txtLogOutput);
            this.Controls.Add(statusContainer);
            this.Controls.Add(cardControlPanel);
        }

        private void ApplySavedSourceSelection()
        {
            string savedSource = _configService.GetValue("DataSource", "paradox");
            bool isCloud = string.Equals(savedSource, "cloud", StringComparison.OrdinalIgnoreCase);
            rbSourceCloud.Checked = isCloud;
            rbSourceParadox.Checked = !isCloud;
            UpdateSyncCheckboxLabel();
        }

        private void SourceRadio_CheckedChanged(object sender, EventArgs e)
        {
            string source = GetSelectedSource();
            _configService.SetValue("DataSource", source);
            UpdateSyncCheckboxLabel();
        }

        private void UpdateSyncCheckboxLabel()
        {
            chkSyncParadox.Text = rbSourceCloud.Checked ? "Sync cloud data first" : "Sync Paradox data first";
        }

        private string GetSelectedSource()
        {
            return rbSourceCloud.Checked ? "cloud" : "paradox";
        }

        private async void BtnProcessEOD_Click(object sender, EventArgs e)
        {
            DateTime startDate = dtpStartDate.Value;
            DateTime endDate = dtpEndDate.Value;
            bool syncFirst = chkSyncParadox.Checked;
            string source = GetSelectedSource();

            string paradoxDir = _configService.GetValue("ParadoxDBFolder", @"C:\Users\MIS-01\Desktop\TESTINGPT2\Data");

            SetUiProcessingState(true);
            txtLogOutput.Clear();

            AppendLog($"[{DateTime.Now:HH:mm:ss}] Initializing EOD Process (Source: {source.ToUpper()})...", Color.Cyan);
            AppendLog($"----------------------------------------------------------------------", Color.Gray);

            try
            {
                // STEP 1: PARADOX SYNC (NATIVE C# ODBC ENGINE)
                if (syncFirst && source == "paradox")
                {
                    AppendLog($"[{DateTime.Now:HH:mm:ss}] Syncing Paradox DB via Native C# Engine from '{paradoxDir}'...", Color.Yellow);

                    SyncResult syncResult = await _syncService.ExecuteBulkSyncAsync();
                    string syncLog = syncResult.Message;
                    bool syncSuccess = syncResult.Success;

                    AppendLog(syncLog.Trim(), syncSuccess ? Color.LightGreen : Color.LightPink);

                    if (!syncSuccess)
                    {
                        lblStatus.Text = "Paradox sync failed.";
                        lblStatus.ForeColor = Color.DarkRed;
                        _logService.LogError($"C# Paradox Sync Failed: {syncLog}", null, "frmProcessEOD");
                        return;
                    }

                    _logService.LogInfo("Synced Paradox DB via Native C# Engine", "frmProcessEOD");
                }

                // STEP 2: LOOP FOR EACH DATE IN RANGE
                for (DateTime date = startDate.Date; date <= endDate.Date; date = date.AddDays(1))
                {
                    string dateStr = date.ToString("yyyy-MM-dd");

                    // CLOUD SYNC (USING PYTHON ENGINE)
                    if (syncFirst && source == "cloud")
                    {
                        AppendLog($"[{DateTime.Now:HH:mm:ss}] Syncing Cloud XML data for {dateStr}...", Color.Yellow);

                        string cloudSyncResult = await _pythonBridge.SyncCloudAsync(dateStr);
                        bool cloudSyncSuccess = !(cloudSyncResult.Contains("ERROR") || cloudSyncResult.Contains("Error") || cloudSyncResult.Contains("Exception"));

                        AppendLog(cloudSyncResult.Trim(), cloudSyncSuccess ? Color.LightGreen : Color.LightPink);

                        if (!cloudSyncSuccess)
                        {
                            AppendLog($"[{DateTime.Now:HH:mm:ss}] Cloud sync failed for {dateStr}, skipping EOD for this date.", Color.LightPink);
                            _logService.LogError($"Cloud XML Sync Failed for {dateStr}: {cloudSyncResult}", null, "frmProcessEOD");
                            continue;
                        }

                        _logService.LogInfo($"Synced Cloud XML data for {dateStr}", "frmProcessEOD");
                    }

                    // EOD GENERATION
                    AppendLog($"[{DateTime.Now:HH:mm:ss}] Generating Greenhills EOD text file for {dateStr} (Source: {source})...", Color.Cyan);

                    string eodResult = await _pythonBridge.GenerateEodAsync(dateStr, source);

                    if (eodResult.Contains("ERROR") || eodResult.Contains("Exception") || eodResult.Contains("FAILED"))
                    {
                        AppendLog($"[{DateTime.Now:HH:mm:ss}] FAILED ({dateStr}):\n{eodResult}", Color.LightPink);
                        _logService.LogError($"EOD Generation failed for {dateStr}: {eodResult}", null, "frmProcessEOD");
                    }
                    else
                    {
                        AppendLog($"[{DateTime.Now:HH:mm:ss}] {eodResult.Trim()}", Color.LightGreen);
                        _logService.LogInfo($"Successfully generated EOD file for {dateStr}", "frmProcessEOD");
                    }
                }

                lblStatus.Text = "Process completed successfully!";
                lblStatus.ForeColor = Color.DarkGreen;
            }
            catch (Exception ex)
            {
                AppendLog($"[{DateTime.Now:HH:mm:ss}] CRITICAL ERROR: {ex.Message}", Color.Red);
                lblStatus.Text = "Process failed.";
                lblStatus.ForeColor = Color.DarkRed;
                _logService.LogError($"Process EOD Critical Failure: {ex.Message}", ex, "frmProcessEOD");
            }
            finally
            {
                SetUiProcessingState(false);
            }
        }

        private void SetUiProcessingState(bool isProcessing)
        {
            btnProcessEOD.Enabled = !isProcessing;
            dtpStartDate.Enabled = !isProcessing;
            dtpEndDate.Enabled = !isProcessing;
            chkSyncParadox.Enabled = !isProcessing;
            rbSourceParadox.Enabled = !isProcessing;
            rbSourceCloud.Enabled = !isProcessing;

            if (isProcessing)
            {
                btnProcessEOD.BackColor = Color.FromArgb(108, 117, 125);
                progressBar.Style = ProgressBarStyle.Marquee;
                lblStatus.Text = "Processing EOD, please wait...";
                lblStatus.ForeColor = Color.FromArgb(13, 110, 253);
            }
            else
            {
                btnProcessEOD.BackColor = Color.FromArgb(13, 110, 253);
                progressBar.Style = ProgressBarStyle.Blocks;
                progressBar.Value = 100;
            }
        }

        private void AppendLog(string message, Color color)
        {
            if (txtLogOutput.InvokeRequired)
            {
                txtLogOutput.Invoke(new Action(() => AppendLog(message, color)));
                return;
            }

            txtLogOutput.SelectionStart = txtLogOutput.TextLength;
            txtLogOutput.SelectionLength = 0;
            txtLogOutput.SelectionColor = color;
            txtLogOutput.AppendText(message + Environment.NewLine);
            txtLogOutput.SelectionColor = txtLogOutput.ForeColor;
            txtLogOutput.ScrollToCaret();
        }
    }
}