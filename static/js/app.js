document.addEventListener('DOMContentLoaded', () => {
    // Format currency numbers
    document.querySelectorAll('.amount').forEach(el => {
        const amount = parseFloat(el.textContent);
        el.textContent = new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND'
        }).format(amount);
    });

    // Format dates
    document.querySelectorAll('.date').forEach(el => {
        const date = new Date(el.textContent);
        el.textContent = new Intl.DateTimeFormat('vi-VN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(date);
    });

    // Handle expense form submission
    const expenseForm = document.getElementById('expense-form');
    if (expenseForm) {
        expenseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(expenseForm);
            
            try {
                const response = await fetch('/api/expenses', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('Failed to add expense');
                }
                
                // Reload page to show new expense
                window.location.reload();
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to add expense. Please try again.');
            }
        });
    }
}); 