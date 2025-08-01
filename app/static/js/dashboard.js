class Dashboard {
    constructor() {
        this.init();
    }
    
    init() {
        this.loadTransactions();
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Sync accounts button
        document.getElementById('sync-btn').addEventListener('click', () => {
            this.syncAccounts();
        });
        
        // Account filter dropdown
        document.getElementById('account-filter').addEventListener('change', (e) => {
            this.loadTransactions(e.target.value);
        });
        
        // Refresh transactions button
        document.getElementById('refresh-transactions').addEventListener('click', () => {
            const accountId = document.getElementById('account-filter').value;
            this.loadTransactions(accountId);
        });
    }
    
    async loadTransactions(accountId = '') {
        try {
            const container = document.getElementById('transactions-container');
            this.showLoading(container);
            
            const url = accountId ? `/api/transactions?account_id=${accountId}` : '/api/transactions';
            const response = await fetch(url);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const transactions = await response.json();
            this.renderTransactions(transactions);
        } catch (error) {
            console.error('Error loading transactions:', error);
            this.showError('Failed to load transactions: ' + error.message);
        }
    }
    
    renderTransactions(transactions) {
        const container = document.getElementById('transactions-container');
        
        if (transactions.length === 0) {
            container.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-inbox display-1 text-muted"></i>
                    <p class="mt-3 text-muted">No transactions found.</p>
                    <button class="btn btn-primary" onclick="dashboard.syncAccounts()">
                        <i class="bi bi-arrow-clockwise"></i> Sync Accounts
                    </button>
                </div>
            `;
            return;
        }
        
        const table = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Account</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Type</th>
                            <th>Customer</th>
                            <th>Description</th>
                            <th>ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${transactions.map(t => this.renderTransactionRow(t)).join('')}
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = table;
    }
    
    renderTransactionRow(transaction) {
        const date = new Date(transaction.stripe_created).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const amount = transaction.amount;
        const amountClass = amount >= 0 ? 'amount-positive' : 'amount-negative';
        const formattedAmount = Math.abs(amount).toFixed(2);
        
        return `
            <tr class="transaction-row">
                <td>
                    <small class="text-muted">${date}</small>
                </td>
                <td>
                    <span class="badge bg-secondary">${transaction.account_name}</span>
                </td>
                <td class="${amountClass}">
                    <span class="currency-code">${transaction.currency}</span> ${formattedAmount}
                </td>
                <td>
                    <span class="badge bg-${this.getStatusColor(transaction.status)} status-badge">
                        ${transaction.status}
                    </span>
                </td>
                <td>
                    <small class="text-muted">${transaction.type}</small>
                </td>
                <td>
                    ${transaction.customer_email ? 
                        `<small>${transaction.customer_email}</small>` : 
                        '<small class="text-muted">N/A</small>'
                    }
                </td>
                <td>
                    ${transaction.description ? 
                        `<small>${this.truncateText(transaction.description, 30)}</small>` : 
                        '<small class="text-muted">N/A</small>'
                    }
                </td>
                <td>
                    <small class="transaction-id">${transaction.stripe_id.substring(0, 12)}...</small>
                </td>
            </tr>
        `;
    }
    
    getStatusColor(status) {
        const statusColors = {
            'succeeded': 'success',
            'pending': 'warning',
            'failed': 'danger',
            'canceled': 'secondary',
            'requires_action': 'info',
            'requires_confirmation': 'info',
            'requires_payment_method': 'warning',
            'processing': 'info'
        };
        return statusColors[status] || 'secondary';
    }
    
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }
    
    showLoading(container) {
        container.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Loading transactions...</p>
            </div>
        `;
    }
    
    async syncAccounts() {
        const btn = document.getElementById('sync-btn');
        const originalContent = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Syncing...';
        
        // Add spinning animation
        const style = document.createElement('style');
        style.textContent = `
            .spin {
                animation: spin 1s linear infinite;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        try {
            const response = await fetch('/api/sync');
            const result = await response.json();
            
            if (result.status === 'success') {
                this.showAlert('All accounts synced successfully!', 'success');
                // Refresh transactions after sync
                const accountId = document.getElementById('account-filter').value;
                this.loadTransactions(accountId);
            } else if (result.status === 'partial_success') {
                this.showAlert(result.message, 'warning');
                // Still refresh transactions
                const accountId = document.getElementById('account-filter').value;
                this.loadTransactions(accountId);
            } else {
                this.showAlert('Error syncing accounts: ' + result.message, 'danger');
            }
        } catch (error) {
            this.showAlert('Error syncing accounts: ' + error.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalContent;
            document.head.removeChild(style);
        }
    }
    
    showAlert(message, type) {
        const alertContainer = document.getElementById('alert-container');
        const alertId = 'alert-' + Date.now();
        
        const alert = document.createElement('div');
        alert.id = alertId;
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            <i class="bi bi-${this.getAlertIcon(type)}"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                alertElement.remove();
            }
        }, 5000);
    }
    
    getAlertIcon(type) {
        const icons = {
            'success': 'check-circle',
            'warning': 'exclamation-triangle',
            'danger': 'x-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showError(message) {
        const container = document.getElementById('transactions-container');
        container.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-exclamation-triangle display-1 text-danger"></i>
                <p class="mt-3 text-danger">${message}</p>
                <button class="btn btn-outline-primary" onclick="dashboard.loadTransactions()">
                    <i class="bi bi-arrow-clockwise"></i> Try Again
                </button>
            </div>
        `;
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
});