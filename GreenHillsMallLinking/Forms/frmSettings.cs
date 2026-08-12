using GH_Mall_Linking.Data;
using GH_Mall_Linking.Services;
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace GH_Mall_Linking.Forms
{
    [System.ComponentModel.DesignerCategory("")]
    public partial class frmSettings : Form
    {
        private readonly ConfigService _configService;

        // Folder Paths
        private TextBox txtParadoxDB, txtACCLocal, txtACCShared, txtCloudDataFolder, txtPythonPath;
        private Button btnBrowseParadox, btnBrowseACCLocal, btnBrowseACCShared, btnBrowseCloudFolder, btnBrowsePython;
        private Button btnTestParadox, btnTestACC, btnTestCloud;

        // POS Configuration
        private TextBox txtPOSCode, txtDepartment, txtTerminal, txtAccountNo;

        // Initial Values
        private TextBox txtGrandTotal, txtZCount, txtBatchLimit;

        // Actions
        private Button btnPaymentMethods, btnChangePassword, btnSave;

        public frmSettings()
        {
            InitializeComponentProgrammatically();
            _configService = new ConfigService();

            WireUpEvents();
            LoadSettings();
        }

        private void InitializeComponentProgrammatically()
        {
            this.Text = "GH Mall Linking — Settings";
            this.BackColor = Color.FromArgb(248, 249, 250);
            this.Padding = new Padding(15);
            this.AutoScroll = true;

            // 1. Folder Paths Group
            var grpFolderPaths = new GroupBox
            {
                Text = "Folder Paths",
                Location = new Point(15, 12),
                Size = new Size(this.ClientSize.Width - 30, 215),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };

            AddFolderRow(grpFolderPaths, "Paradox DB Folder:", 28, out txtParadoxDB, out btnBrowseParadox);
            AddFolderRow(grpFolderPaths, "ACC Local Folder:", 60, out txtACCLocal, out btnBrowseACCLocal);
            AddFolderRow(grpFolderPaths, "ACC Shared Folder:", 92, out txtACCShared, out btnBrowseACCShared);
            AddFolderRow(grpFolderPaths, "Cloud Data Folder:", 124, out txtCloudDataFolder, out btnBrowseCloudFolder);

            // Test buttons (Anchored relative to panel width)
            btnTestParadox = new Button { Text = "Test Paradox", Location = new Point(140, 168), Size = new Size(130, 32) };
            btnTestACC = new Button { Text = "Test ACC Folders", Location = new Point(280, 168), Size = new Size(130, 32) };
            btnTestCloud = new Button { Text = "Test Cloud", Location = new Point(420, 168), Size = new Size(110, 32) };

            StyleButton(btnTestParadox);
            StyleButton(btnTestACC);
            StyleButton(btnTestCloud);

            grpFolderPaths.Controls.Add(btnTestParadox);
            grpFolderPaths.Controls.Add(btnTestACC);
            grpFolderPaths.Controls.Add(btnTestCloud);

            // 2. POS Configuration Group
            var grpPOSConfig = new GroupBox
            {
                Text = "POS Configuration",
                Location = new Point(15, 237),
                Size = new Size(this.ClientSize.Width - 30, 105),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };

            // Row 1: POS Code (Col 1), Department (Col 2), Terminal (Col 3)
            txtPOSCode = AddLabeledField(grpPOSConfig, "POS Code:", 15, 30, 100, 75);
            txtDepartment = AddLabeledField(grpPOSConfig, "Department:", 205, 30, 100, 85);
            txtTerminal = AddLabeledField(grpPOSConfig, "Terminal:", 400, 30, 70, 65);

            // Row 2: Account No
            txtAccountNo = AddLabeledField(grpPOSConfig, "Account No:", 15, 65, 120, 85);

            // 3. Initial Values Group
            var grpInitialValues = new GroupBox
            {
                Text = "Initial Values (First Run Only)",
                Location = new Point(15, 352),
                Size = new Size(this.ClientSize.Width - 30, 75),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };

            // Adjusted X offsets to prevent text collision ("Batch Limit" overlapping text box)
            txtGrandTotal = AddLabeledField(grpInitialValues, "Grand Total:", 15, 30, 90, 85);
            txtZCount = AddLabeledField(grpInitialValues, "Z-Count:", 205, 30, 70, 60);
            txtBatchLimit = AddLabeledField(grpInitialValues, "Batch Limit:", 355, 30, 70, 80);

            // 4. Bottom Action Buttons
            btnPaymentMethods = new Button
            {
                Text = "💳 Payment Methods",
                Location = new Point(15, 440),
                Size = new Size(155, 36)
            };
            StyleButton(btnPaymentMethods);

            btnChangePassword = new Button
            {
                Text = "🔑 Change Password",
                Location = new Point(180, 440),
                Size = new Size(155, 36)
            };
            StyleButton(btnChangePassword);

            btnSave = new Button
            {
                Text = "💾 Save Settings",
                Location = new Point(this.ClientSize.Width - 155, 440),
                Size = new Size(140, 36),
                Anchor = AnchorStyles.Top | AnchorStyles.Right,
                BackColor = Color.FromArgb(13, 110, 253),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnSave.FlatAppearance.BorderSize = 0;

            this.Controls.Add(grpFolderPaths);
            this.Controls.Add(grpPOSConfig);
            this.Controls.Add(grpInitialValues);
            this.Controls.Add(btnPaymentMethods);
            this.Controls.Add(btnChangePassword);
            this.Controls.Add(btnSave);

            // Python Path (Hidden controls maintained for service requirements)
            txtPythonPath = new TextBox();
            btnBrowsePython = new Button { Text = "Browse..." };
        }

        private void AddFolderRow(GroupBox parent, string labelText, int y, out TextBox textBox, out Button browseButton)
        {
            var label = new Label
            {
                Text = labelText,
                Location = new Point(15, y + 3),
                AutoSize = true,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Regular)
            };

            textBox = new TextBox
            {
                Location = new Point(140, y),
                Size = new Size(parent.Width - 200, 23),
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Font = new Font("Segoe UI", 9F)
            };

            browseButton = new Button
            {
                Text = "...",
                Location = new Point(parent.Width - 52, y - 1),
                Size = new Size(38, 25),
                Anchor = AnchorStyles.Top | AnchorStyles.Right,
                Cursor = Cursors.Hand
            };
            StyleButton(browseButton);

            parent.Controls.Add(label);
            parent.Controls.Add(textBox);
            parent.Controls.Add(browseButton);
        }

        private TextBox AddLabeledField(GroupBox parent, string labelText, int x, int y, int fieldWidth, int labelWidth = 70)
        {
            var label = new Label
            {
                Text = labelText,
                Location = new Point(x, y + 3),
                AutoSize = true,
                Font = new Font("Segoe UI", 8.5F, FontStyle.Regular)
            };

            var textBox = new TextBox
            {
                Location = new Point(x + labelWidth, y),
                Size = new Size(fieldWidth, 23),
                Font = new Font("Segoe UI", 9F)
            };

            parent.Controls.Add(label);
            parent.Controls.Add(textBox);
            return textBox;
        }

        private void StyleButton(Button btn)
        {
            btn.BackColor = Color.FromArgb(238, 240, 243);
            btn.ForeColor = Color.FromArgb(33, 37, 41);
            btn.FlatStyle = FlatStyle.Flat;
            btn.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            btn.Cursor = Cursors.Hand;
            btn.FlatAppearance.BorderColor = Color.FromArgb(200, 205, 210);
            btn.FlatAppearance.BorderSize = 1;
        }

        private void WireUpEvents()
        {
            if (btnBrowseParadox != null) btnBrowseParadox.Click += (s, e) => BrowseFolder(txtParadoxDB);
            if (btnBrowseACCLocal != null) btnBrowseACCLocal.Click += (s, e) => BrowseFolder(txtACCLocal);
            if (btnBrowseACCShared != null) btnBrowseACCShared.Click += (s, e) => BrowseFolder(txtACCShared);
            if (btnBrowseCloudFolder != null) btnBrowseCloudFolder.Click += (s, e) => BrowseFolder(txtCloudDataFolder);

            if (btnBrowsePython != null && txtPythonPath != null)
                btnBrowsePython.Click += (s, e) => BrowseFile(txtPythonPath, "Executable Files (*.exe)|*.exe|All Files (*.*)|*.*");

            if (btnTestParadox != null) btnTestParadox.Click += BtnTestParadox_Click;
            if (btnTestACC != null) btnTestACC.Click += BtnTestACC_Click;
            if (btnTestCloud != null) btnTestCloud.Click += BtnTestCloud_Click;

            if (btnPaymentMethods != null) btnPaymentMethods.Click += (s, e) => (this.ParentForm as frmDashboardOverview)?.OpenChildForm(new frmPaymentMethods());
            if (btnChangePassword != null) btnChangePassword.Click += (s, e) => new frmChangePassword().ShowDialog(this);

            if (btnSave != null) btnSave.Click += BtnSave_Click;
        }

        private void BtnTestParadox_Click(object sender, EventArgs e)
        {
            string folderPath = txtParadoxDB != null ? txtParadoxDB.Text.Trim() : "";

            if (string.IsNullOrWhiteSpace(folderPath) || !Directory.Exists(folderPath))
            {
                MessageBox.Show(
                    "The specified Paradox database folder does not exist!\nPlease select a valid directory.",
                    "Paradox Connection Test Failed",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            string[] requiredFiles = { "ORDERS", "ORDITEM", "ORDPAY" };
            var missingFiles = new List<string>();

            foreach (string baseFileName in requiredFiles)
            {
                bool found = File.Exists(Path.Combine(folderPath, baseFileName)) ||
                             File.Exists(Path.Combine(folderPath, baseFileName + ".DB")) ||
                             File.Exists(Path.Combine(folderPath, baseFileName + ".db")) ||
                             File.Exists(Path.Combine(folderPath, baseFileName.ToLower() + ".db"));

                if (!found)
                {
                    missingFiles.Add($"{baseFileName}.DB");
                }
            }

            if (missingFiles.Count == 0)
            {
                MessageBox.Show(
                    $"Paradox Folder Test Successful!\n\nAll required database files were found in:\n{folderPath}",
                    "Paradox Connection Success",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            else
            {
                string missingList = string.Join("\n • ", missingFiles);
                MessageBox.Show(
                    $"Folder exists, but missing key Paradox files:\n • {missingList}\n\nPlease check if you selected the correct folder.",
                    "Paradox Files Missing",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
            }
        }

        private void BtnTestACC_Click(object sender, EventArgs e)
        {
            string localFolder = txtACCLocal != null ? txtACCLocal.Text.Trim() : "";
            string sharedFolder = txtACCShared != null ? txtACCShared.Text.Trim() : "";

            bool localValid = !string.IsNullOrWhiteSpace(localFolder) && Directory.Exists(localFolder);
            bool sharedValid = !string.IsNullOrWhiteSpace(sharedFolder) && Directory.Exists(sharedFolder);

            string statusMessage = "";

            if (localValid)
                statusMessage += $"✓ ACC Local Folder: ACCESSIBLE ({localFolder})\n";
            else
                statusMessage += $"✗ ACC Local Folder: INVALID OR DOES NOT EXIST ({localFolder})\n";

            if (!string.IsNullOrWhiteSpace(sharedFolder))
            {
                if (sharedValid)
                    statusMessage += $"✓ ACC Shared Folder: ACCESSIBLE ({sharedFolder})";
                else
                    statusMessage += $"✗ ACC Shared Folder: INVALID OR UNREACHABLE ({sharedFolder})";
            }
            else
            {
                statusMessage += "ℹ ACC Shared Folder: (Not Configured / Optional)";
            }

            MessageBoxIcon icon = localValid ? MessageBoxIcon.Information : MessageBoxIcon.Warning;
            MessageBox.Show(statusMessage, "ACC Folders Test", MessageBoxButtons.OK, icon);
        }

        private void BtnTestCloud_Click(object sender, EventArgs e)
        {
            string path = txtCloudDataFolder != null ? txtCloudDataFolder.Text.Trim() : "";
            if (!string.IsNullOrWhiteSpace(path) && Directory.Exists(path))
            {
                var files = Directory.GetFiles(path, "*.xml", SearchOption.AllDirectories);
                if (files.Length > 0)
                {
                    MessageBox.Show($"Success! Found {files.Length} XML file(s) in subfolders.", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }
                else
                {
                    MessageBox.Show($"Folder exists, but no .xml files were found in: {path}", "No XML Files Found", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
            }
            else
            {
                MessageBox.Show("The specified Cloud Data folder does not exist or is empty.", "Cloud Folder Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void BrowseFolder(TextBox targetTextBox)
        {
            using (FolderBrowserDialog fbd = new FolderBrowserDialog())
            {
                if (targetTextBox != null && Directory.Exists(targetTextBox.Text))
                {
                    fbd.SelectedPath = targetTextBox.Text;
                }

                if (fbd.ShowDialog() == DialogResult.OK && targetTextBox != null)
                {
                    targetTextBox.Text = fbd.SelectedPath;
                }
            }
        }

        private void BrowseFile(TextBox targetTextBox, string filter)
        {
            using (OpenFileDialog ofd = new OpenFileDialog())
            {
                ofd.Filter = filter;
                if (ofd.ShowDialog() == DialogResult.OK && targetTextBox != null)
                {
                    targetTextBox.Text = ofd.FileName;
                }
            }
        }

        private void LoadSettings()
        {
            this.SuspendLayout();

            try
            {
                if (txtParadoxDB != null) txtParadoxDB.Text = _configService.GetValue("ParadoxDBFolder", @"C:\Users\MIS-01\Downloads\Data");
                if (txtACCLocal != null) txtACCLocal.Text = _configService.GetValue("AccLocalFolder", @"C:\GH_ACC_EXPORT");
                if (txtACCShared != null) txtACCShared.Text = _configService.GetValue("AccSharedFolder", "");
                if (txtCloudDataFolder != null) txtCloudDataFolder.Text = _configService.GetValue("CloudDataFolder", "");
                if (txtPythonPath != null) txtPythonPath.Text = _configService.GetValue("PythonPath", @"C:\Python39\python.exe");

                if (txtPOSCode != null) txtPOSCode.Text = _configService.GetValue("PosCode", "POS01");
                if (txtDepartment != null) txtDepartment.Text = _configService.GetValue("Department", "MIS");
                if (txtTerminal != null) txtTerminal.Text = _configService.GetValue("TerminalNo", "01");
                if (txtAccountNo != null) txtAccountNo.Text = _configService.GetValue("AccountNo", "");

                if (txtGrandTotal != null) txtGrandTotal.Text = _configService.GetValue("GrandTotal", "0.00");
                if (txtZCount != null) txtZCount.Text = _configService.GetValue("ZCount", "0");
                if (txtBatchLimit != null) txtBatchLimit.Text = _configService.GetValue("BatchLimit", "0");
            }
            finally
            {
                this.ResumeLayout(true);
            }
        }

        private async void BtnSave_Click(object sender, EventArgs e)
        {
            var mainDashboard = this.ParentForm as frmDashboardOverview;

            try
            {
                if (btnSave != null) btnSave.Enabled = false;
                if (mainDashboard != null) mainDashboard.SetSidebarEnabled(false);
                this.Cursor = Cursors.WaitCursor;

                var settingsToSave = new Dictionary<string, string>();
                if (txtParadoxDB != null) settingsToSave["ParadoxDBFolder"] = txtParadoxDB.Text.Trim();
                if (txtACCLocal != null) settingsToSave["AccLocalFolder"] = txtACCLocal.Text.Trim();
                if (txtACCShared != null) settingsToSave["AccSharedFolder"] = txtACCShared.Text.Trim();
                if (txtCloudDataFolder != null) settingsToSave["CloudDataFolder"] = txtCloudDataFolder.Text.Trim();
                if (txtPythonPath != null) settingsToSave["PythonPath"] = txtPythonPath.Text.Trim();

                if (txtPOSCode != null) settingsToSave["PosCode"] = txtPOSCode.Text.Trim();
                if (txtDepartment != null) settingsToSave["Department"] = txtDepartment.Text.Trim();
                if (txtTerminal != null) settingsToSave["TerminalNo"] = txtTerminal.Text.Trim();
                if (txtAccountNo != null) settingsToSave["AccountNo"] = txtAccountNo.Text.Trim();

                if (txtGrandTotal != null) settingsToSave["GrandTotal"] = txtGrandTotal.Text.Trim();
                if (txtZCount != null) settingsToSave["ZCount"] = txtZCount.Text.Trim();
                if (txtBatchLimit != null) settingsToSave["BatchLimit"] = txtBatchLimit.Text.Trim();

                await Task.Run(() => _configService.SetValues(settingsToSave));

                MessageBox.Show("Settings have been saved successfully!", "Settings Saved", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"An error occurred while saving settings:\n{ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                if (btnSave != null) btnSave.Enabled = true;
                if (mainDashboard != null) mainDashboard.SetSidebarEnabled(true);
                this.Cursor = Cursors.Default;
            }
        }
    }
}