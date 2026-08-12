using GH_Mall_Linking.Data;
using GH_Mall_Linking.Models;
using System;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace GH_Mall_Linking.Forms
{
    [System.ComponentModel.DesignerCategory("")]
    public partial class frmPaymentMethods : Form
    {
        private AppDbContext _context;
        private DataGridView grid;
        private Button btnAdd;
        private Button btnDelete;
        private Button btnSave;
        private Button btnRefresh;
        private Label lblStatus;

        public frmPaymentMethods()
        {
            InitializeComponentProgrammatically();
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            LoadData();
        }

        private void InitializeComponentProgrammatically()
        {
            this.BackColor = Color.FromArgb(248, 249, 250);
            this.Padding = new Padding(20);

            // Title Label
            Label lblTitle = new Label
            {
                Text = "Payment Methods Configuration",
                Font = new Font("Segoe UI", 13f, FontStyle.Bold),
                ForeColor = Color.FromArgb(33, 37, 41),
                Location = new Point(20, 15),
                AutoSize = true
            };

            // Top Action Bar / Toolbar
            Panel toolbar = new Panel
            {
                Location = new Point(20, 50),
                Height = 36,
                Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right,
                Width = this.ClientSize.Width - 40
            };

            btnAdd = CreateButton("+ Add Method", 0, 0, 110, 32, Color.FromArgb(235, 238, 242), Color.Black);
            btnAdd.Click += BtnAdd_Click;

            btnDelete = CreateButton("Delete Selected", 120, 0, 120, 32, Color.FromArgb(255, 235, 235), Color.DarkRed);
            btnDelete.Click += BtnDelete_Click;

            btnRefresh = CreateButton("\U0001F504 Refresh", 250, 0, 90, 32, Color.FromArgb(235, 238, 242), Color.Black);
            btnRefresh.Click += (s, e) => LoadData();

            btnSave = CreateButton("\U0001F4BE Save Changes", toolbar.Width - 140, 0, 140, 32, Color.FromArgb(0, 122, 204), Color.White);
            btnSave.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            btnSave.Click += BtnSave_Click;

            toolbar.Controls.Add(btnAdd);
            toolbar.Controls.Add(btnDelete);
            toolbar.Controls.Add(btnRefresh);
            toolbar.Controls.Add(btnSave);

            // DataGridView Setup - dynamically resized
            grid = new DataGridView
            {
                Location = new Point(20, 95),
                Size = new Size(this.ClientSize.Width - 40, this.ClientSize.Height - 140),
                Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right,
                AllowUserToAddRows = false,
                AllowUserToDeleteRows = false,
                AutoGenerateColumns = true,
                AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill,
                SelectionMode = DataGridViewSelectionMode.FullRowSelect,
                MultiSelect = true,
                RowHeadersVisible = false,
                BackgroundColor = Color.White,
                BorderStyle = BorderStyle.Fixed3D,
                EnableHeadersVisualStyles = false
            };

            // Modern Grid Styling
            grid.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(240, 242, 245);
            grid.ColumnHeadersDefaultCellStyle.ForeColor = Color.FromArgb(50, 50, 50);
            grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            grid.ColumnHeadersHeight = 32;

            // Stronger, more obvious selection highlight so it's clear which row(s)
            // are currently chosen before hitting Delete or editing them.
            grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(13, 110, 253);
            grid.DefaultCellStyle.SelectionForeColor = Color.White;
            grid.DefaultCellStyle.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);
            grid.RowTemplate.Height = 28;

            // Clicking directly on a checkbox cell (Default/Active columns) toggles the
            // checkbox but doesn't always visually select/highlight the row on its own --
            // force the whole row selected on any cell click so the highlight is
            // consistent no matter which column the user clicks.
            grid.CellClick += (s, e) =>
            {
                if (e.RowIndex >= 0 && e.RowIndex < grid.Rows.Count)
                {
                    grid.ClearSelection();
                    grid.Rows[e.RowIndex].Selected = true;
                }
            };

            // Status Bar Label
            lblStatus = new Label
            {
                Text = "Ready",
                Location = new Point(20, this.ClientSize.Height - 35),
                Anchor = AnchorStyles.Bottom | AnchorStyles.Left,
                AutoSize = true,
                ForeColor = Color.Gray,
                Font = new Font("Segoe UI", 9F)
            };

            this.Controls.Add(lblTitle);
            this.Controls.Add(toolbar);
            this.Controls.Add(grid);
            this.Controls.Add(lblStatus);
        }

        private Button CreateButton(string text, int x, int y, int w, int h, Color bg, Color fg)
        {
            Button btn = new Button
            {
                Text = text,
                Location = new Point(x, y),
                Size = new Size(w, h),
                BackColor = bg,
                ForeColor = fg,
                FlatStyle = FlatStyle.Flat,
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 9F, FontStyle.Regular)
            };
            btn.FlatAppearance.BorderSize = 1;
            btn.FlatAppearance.BorderColor = Color.FromArgb(200, 200, 200);
            return btn;
        }

        private void LoadData()
        {
            try
            {
                _context?.Dispose();
                _context = new AppDbContext();
                _context.Database.EnsureCreated();

                // Plain List<T>, not BindingList<T> -- BindingList's ListChanged events
                // were re-entering FormatGridColumns() mid-configuration and causing a
                // NullReferenceException. Edits still write back fine because the grid
                // rows hold references to the same tracked EF entities.
                var methods = _context.PaymentMethods.OrderBy(p => p.Id).ToList();

                grid.DataSource = null;
                grid.AutoGenerateColumns = true;
                grid.DataSource = methods;

                FormatGridColumns();

                lblStatus.Text = $"{methods.Count} payment method(s) loaded.";
                lblStatus.ForeColor = Color.Gray;
            }
            catch (Exception ex)
            {
                lblStatus.Text = "Database connection error.";
                lblStatus.ForeColor = Color.Red;
                MessageBox.Show($"Error loading PaymentMethods table:\n{ex.Message}", "Database Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void FormatGridColumns()
        {
            if (grid.Columns["Id"] != null)
            {
                grid.Columns["Id"].ReadOnly = true;
                grid.Columns["Id"].FillWeight = 30;
                grid.Columns["Id"].HeaderText = "ID";
            }

            if (grid.Columns["MethodName"] != null)
            {
                grid.Columns["MethodName"].HeaderText = "Method Name";
                grid.Columns["MethodName"].FillWeight = 150;
            }

            if (grid.Columns["GhCode"] != null)
            {
                grid.Columns["GhCode"].HeaderText = "GH Code";
                grid.Columns["GhCode"].FillWeight = 60;
            }

            if (grid.Columns["IsDefault"] != null)
            {
                grid.Columns["IsDefault"].HeaderText = "Default";
                grid.Columns["IsDefault"].FillWeight = 50;
            }

            if (grid.Columns["IsActive"] != null)
            {
                grid.Columns["IsActive"].HeaderText = "Active";
                grid.Columns["IsActive"].FillWeight = 50;
            }

            if (grid.Columns["CreatedAt"] != null)
            {
                grid.Columns["CreatedAt"].ReadOnly = true;
                grid.Columns["CreatedAt"].HeaderText = "Created At";
                grid.Columns["CreatedAt"].FillWeight = 110;
            }
        }

        private void BtnAdd_Click(object sender, EventArgs e)
        {
            try
            {
                var newMethod = new PaymentMethod
                {
                    MethodName = "NEW PAYMENT",
                    GhCode = "00",
                    IsDefault = false,
                    IsActive = true,
                    CreatedAt = DateTime.Now
                };

                _context.PaymentMethods.Add(newMethod);
                _context.SaveChanges();

                LoadData();
                lblStatus.Text = "New record added. Edit details directly in the grid.";
                lblStatus.ForeColor = Color.Green;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Unable to add new payment method:\n{ex.Message}", "Add Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void BtnDelete_Click(object sender, EventArgs e)
        {
            if (grid.SelectedRows.Count == 0)
            {
                MessageBox.Show("Please select one or more payment methods to delete.", "Selection Required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            var confirm = MessageBox.Show(
                $"Are you sure you want to delete {grid.SelectedRows.Count} selected record(s)?",
                "Confirm Delete", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);

            if (confirm != DialogResult.Yes) return;

            try
            {
                foreach (DataGridViewRow row in grid.SelectedRows)
                {
                    if (row.DataBoundItem is PaymentMethod item)
                    {
                        var entity = _context.PaymentMethods.Find(item.Id);
                        if (entity != null)
                        {
                            _context.PaymentMethods.Remove(entity);
                        }
                    }
                }

                _context.SaveChanges();
                LoadData();

                lblStatus.Text = "Selected payment method(s) deleted successfully.";
                lblStatus.ForeColor = Color.DarkGreen;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to delete selected item(s):\n{ex.Message}", "Delete Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void BtnSave_Click(object sender, EventArgs e)
        {
            try
            {
                grid.EndEdit();

                var methods = _context.PaymentMethods.Local.ToList();
                var defaults = methods.Where(m => m.IsDefault).ToList();

                if (defaults.Count > 1)
                {
                    var lastSelected = defaults.Last();
                    foreach (var m in defaults)
                    {
                        if (m != lastSelected) m.IsDefault = false;
                    }
                }

                _context.SaveChanges();
                LoadData();

                lblStatus.Text = "All changes saved successfully!";
                lblStatus.ForeColor = Color.Green;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Failed to save changes:\n{ex.Message}", "Save Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            _context?.Dispose();
            base.OnFormClosed(e);
        }
    }
}