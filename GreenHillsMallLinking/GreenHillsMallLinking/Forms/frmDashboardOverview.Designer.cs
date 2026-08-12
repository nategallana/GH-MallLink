namespace GH_Mall_Linking.Forms
{
    partial class frmDashboardOverview
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            components = new System.ComponentModel.Container();
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frmDashboardOverview));
            panelHeader = new Panel();
            headerLabel = new Label();
            MinimizeIcon = new ImageList(components);
            mainPanel = new Panel();
            panelHeader.SuspendLayout();
            SuspendLayout();
            // 
            // panelHeader
            // 
            panelHeader.BackColor = Color.White;
            panelHeader.BorderStyle = BorderStyle.FixedSingle;
            panelHeader.Controls.Add(headerLabel);
            panelHeader.Dock = DockStyle.Top;
            panelHeader.Location = new Point(0, 0);
            panelHeader.Margin = new Padding(4, 3, 4, 3);
            panelHeader.Name = "panelHeader";
            panelHeader.Size = new Size(730, 60);
            panelHeader.TabIndex = 0;
            panelHeader.Paint += panelHeader_Paint;
            // 
            // headerLabel
            // 
            headerLabel.AutoSize = true;
            headerLabel.BackColor = Color.Transparent;
            headerLabel.Font = new Font("Century Gothic", 15.75F, FontStyle.Bold, GraphicsUnit.Point, 0);
            headerLabel.ForeColor = Color.Black;
            headerLabel.Location = new Point(279, 16);
            headerLabel.Margin = new Padding(4, 0, 4, 0);
            headerLabel.Name = "headerLabel";
            headerLabel.Size = new Size(170, 25);
            headerLabel.TabIndex = 0;
            headerLabel.Text = "GH Mall Linking";
            headerLabel.TextAlign = ContentAlignment.TopCenter;
            headerLabel.Click += label1_Click;
            // 
            // MinimizeIcon
            // 
            MinimizeIcon.ColorDepth = ColorDepth.Depth8Bit;
            MinimizeIcon.ImageStream = (ImageListStreamer)resources.GetObject("MinimizeIcon.ImageStream");
            MinimizeIcon.TransparentColor = Color.Transparent;
            MinimizeIcon.Images.SetKeyName(0, "MinimizeIcon.png");
            MinimizeIcon.Images.SetKeyName(1, "MinimizeIcon2.png");
            MinimizeIcon.Images.SetKeyName(2, "ExitIcon.jpg");
            MinimizeIcon.Images.SetKeyName(3, "MergingIcon.png");
            MinimizeIcon.Images.SetKeyName(4, "LogsIcon.png");
            MinimizeIcon.Images.SetKeyName(5, "SettingsIcon.png");
            MinimizeIcon.Images.SetKeyName(6, "PaymentMethodsIcon.png");
            MinimizeIcon.Images.SetKeyName(7, "SyncIcon.png");
            MinimizeIcon.Images.SetKeyName(8, "ProcessEODIcon.png");
            // 
            // mainPanel
            // 
            mainPanel.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
            mainPanel.BackColor = Color.LightGray;
            mainPanel.Location = new Point(233, 60);
            mainPanel.Margin = new Padding(4, 3, 4, 3);
            mainPanel.Name = "mainPanel";
            mainPanel.Size = new Size(497, 480);
            mainPanel.TabIndex = 2;
            mainPanel.Paint += mainPanel_Paint;
            // 
            // frmDashboardOverview
            // 
            AutoScaleDimensions = new SizeF(7F, 15F);
            AutoScaleMode = AutoScaleMode.Font;
            BackColor = Color.DarkGray;
            ClientSize = new Size(730, 540);
            Controls.Add(mainPanel);
            Controls.Add(panelHeader);
            FormBorderStyle = FormBorderStyle.None;
            Margin = new Padding(4, 3, 4, 3);
            Name = "frmDashboardOverview";
            Text = "GH Mall Linking - Dashboard";
            panelHeader.ResumeLayout(false);
            panelHeader.PerformLayout();
            ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Panel panelHeader;
        private System.Windows.Forms.Label headerLabel;
        private System.Windows.Forms.ImageList MinimizeIcon;
        private System.Windows.Forms.Panel mainPanel;
    }
}