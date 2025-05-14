document.addEventListener('DOMContentLoaded', () => {
    // Initialize date range picker
    $('#daterange').daterangepicker({
        ranges: {
            'Hôm nay': [moment(), moment()],
            '7 ngày qua': [moment().subtract(6, 'days'), moment()],
            '30 ngày qua': [moment().subtract(29, 'days'), moment()],
            'Tháng này': [moment().startOf('month'), moment().endOf('month')],
            'Tháng trước': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
        },
        locale: {
            format: 'DD/MM/YYYY'
        },
        startDate: moment().subtract(6, 'days'),
        endDate: moment()
    });

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

    // Handle inline editing
    document.querySelectorAll('.editable, .editable-select').forEach(el => {
        el.addEventListener('blur', async function() {
            const expenseId = this.closest('tr').dataset.expenseId;
            const field = this.dataset.field;
            let value = this.tagName.toLowerCase() === 'select' ? this.value : this.textContent.trim();

            // Convert amount string to number
            if (field === 'amount') {
                value = parseFloat(value.replace(/[,.]/g, ''));
            }

            try {
                const response = await fetch(`/api/expenses/${expenseId}/field`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        [field]: value
                    })
                });

                if (!response.ok) {
                    throw new Error('Update failed');
                }

                const data = await response.json();
                
                // Update UI with formatted values
                if (field === 'amount') {
                    this.textContent = new Intl.NumberFormat('vi-VN').format(data.amount);
                }
            } catch (error) {
                console.error('Error:', error);
                alert('Có lỗi xảy ra khi cập nhật. Vui lòng thử lại.');
                location.reload();
            }
        });

        // Prevent new line in contenteditable
        if (el.classList.contains('editable')) {
            el.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.blur();
                }
            });
        }
    });
}); 