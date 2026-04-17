document.addEventListener('DOMContentLoaded', () => {

    const currentPath = window.location.pathname;
    
    // Auth Form Handling
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            // Simulate authentication success
            window.location.href = 'dashboard.html';
        });
    }

    // --- Search Page Logic ---
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const hshdNum = document.getElementById('hshd_num').value;
            const resultsDiv = document.getElementById('results');
            
            // Show loading state
            resultsDiv.innerHTML = `<p style="color: var(--text-muted);">Fetching live transactions for Household ${hshdNum} from Azure SQL...</p>`;
            
            try {
                // Live fetch to Azure backend
                const response = await fetch(`https://brandshift-api-dhiren-ereffhe9cqcfhhe4.westus2-01.azurewebsites.net/api/searchdata?hshd_num=${encodeURIComponent(hshdNum)}`);
                
                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
                
                const dbData = await response.json();
                
                if (dbData.length === 0) {
                     resultsDiv.innerHTML = `<p style="color: var(--status-danger);">No transactions found for highly engaged Household ${hshdNum}.</p>`;
                     return;
                }
                
                renderLiveTable(resultsDiv, dbData);
            } catch (error) {
                console.error("Fetch error: ", error);
                resultsDiv.innerHTML = `<p style="color: var(--status-danger);">Error fetching data: ${error.message} <br/><br/><span style="font-size: 0.8em">Note: Ensure your Azure SQL Database connection string is strictly set in Azure Application Settings, and CORS is enabled via Azure portal.</span></p>`;
            }
        });
    }

    const hh10Btn = document.getElementById('hh10-btn');
    if (hh10Btn) {
        hh10Btn.addEventListener('click', async () => {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = `<p style="color: var(--text-muted);">Fetching pre-configured data pull for Household 10...</p>`;
            try {
                const response = await fetch(`https://brandshift-api-dhiren-ereffhe9cqcfhhe4.westus2-01.azurewebsites.net/api/gethousehold10`);
                if (!response.ok) throw new Error(`Server returned ${response.status}`);
                const dbData = await response.json();
                renderLiveTable(resultsDiv, dbData);
            } catch (error) {
                resultsDiv.innerHTML = `<p style="color: var(--status-danger);">Error: ${error.message}</p>`;
            }
        });
    }

    function renderLiveTable(container, data) {
        let html = `
            <div class="data-table-container">
                <table class="brand-table">
                    <thead>
                        <tr>
                            <th>HSHD_NUM</th>
                            <th>Basket_num</th>
                            <th>Date</th>
                            <th>Product_num</th>
                            <th>Department</th>
                            <th>Commodity</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        data.forEach(row => {
            // Formatting exact column names as defined dynamically by our python PyODBC columns
            html += `
                <tr>
                    <td>${row.Hshd_num}</td>
                    <td>${row.Basket_num}</td>
                    <td>${row.Date}</td>
                    <td>${row.Product_num}</td>
                    <td>${row.Department || 'N/A'}</td>
                    <td>${row.Commodity || 'N/A'}</td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
    }

    // --- Upload Page Logic ---
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('csv-file');
    const uploadStatus = document.getElementById('upload-status');

    if (uploadArea && fileInput) {
        uploadArea.addEventListener('click', () => fileInput.click());
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileUpload(e.target.files[0]);
            }
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                handleFileUpload(e.dataTransfer.files[0]);
            }
        });
    }

    async function handleFileUpload(file) {
        uploadStatus.innerHTML = `<p style="color: var(--accent-cyan);">Streaming ${file.name} directly to Azure backend...</p>`;
        
        // Use FormData to safely package multi-part uploads
        const formData = new FormData();
        formData.append('csv-file', file);
        
        try {
            const response = await fetch('https://brandshift-api-dhiren-ereffhe9cqcfhhe4.westus2-01.azurewebsites.net/api/uploaddata', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.text();
                 throw new Error(errorData || "Failed to upload.");
            }
            
            const resultData = await response.json();
            
            uploadStatus.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid var(--status-success); padding: 16px; border-radius: 8px; margin-top: 16px;">
                    <p style="color: var(--status-success); margin: 0;"><strong>Success!</strong> ${resultData.message || (file.name + ' successfully pushed to Azure SQL.')}</p>
                </div>
            `;
        } catch (error) {
             console.error("Upload error: ", error);
             uploadStatus.innerHTML = `
                <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid var(--status-danger); padding: 16px; border-radius: 8px; margin-top: 16px;">
                    <p style="color: var(--status-danger); margin: 0;"><strong>Upload Failed:</strong> ${error.message}</p>
                </div>
            `;
        }
    }

    // --- Dashboard Page Logic (Chart.js implementation) ---
    if (document.getElementById('spendShiftChart') && typeof Chart !== 'undefined') {
        initDashboardCharts();
    }

    function initDashboardCharts() {
        const ctxSpend = document.getElementById('spendShiftChart').getContext('2d');
        const ctxChurn = document.getElementById('churnChart') ? document.getElementById('churnChart').getContext('2d') : null;

        new Chart(ctxSpend, {
            type: 'line',
            data: {
                labels: ['Q1 2018', 'Q2 2018', 'Q3 2018', 'Q4 2018', 'Q1 2019', 'Q2 2019', 'Q3 2019', 'Q4 2019'],
                datasets: [
                    {
                        label: 'National Brand Spend',
                        data: [12000, 11500, 10800, 10500, 9800, 9500, 9200, 8900],
                        borderColor: '#9CA3AF',
                        backgroundColor: 'rgba(156, 163, 175, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Private Label & Organic Spend',
                        data: [4000, 4800, 5600, 6500, 7800, 8500, 9300, 10100],
                        borderColor: '#00F0FF',
                        backgroundColor: 'rgba(0, 240, 255, 0.1)',
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { labels: { color: '#F3F4F6' } }, title: { display: false } },
                scales: {
                    x: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } },
                    y: { ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
                }
            }
        });

        if (ctxChurn) {
            new Chart(ctxChurn, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                    datasets: [
                        {
                            label: 'Active High-Value Demographics',
                            data: [450, 440, 420, 390, 350, 310],
                            backgroundColor: 'rgba(16, 185, 129, 0.8)'
                        },
                        {
                            label: 'At-Risk (High Disengagement Probability)',
                            data: [20, 35, 60, 95, 125, 180],
                            backgroundColor: 'rgba(239, 68, 68, 0.8)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: '#F3F4F6' } } },
                    scales: {
                        x: { stacked: true, ticks: { color: '#9CA3AF' }, grid: { display: false } },
                        y: { stacked: true, ticks: { color: '#9CA3AF' }, grid: { color: 'rgba(255, 255, 255, 0.05)' } }
                    }
                }
            });
        }
    }
});
