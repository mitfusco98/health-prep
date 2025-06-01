// charts.js - Chart visualizations for HealthPrep application

document.addEventListener('DOMContentLoaded', function() {
    // Function to create a vital signs trend chart
    function createVitalsChart(canvasId, labels, systolicData, diastolicData) {
        if (!document.getElementById(canvasId)) return;
        
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Systolic BP',
                        data: systolicData,
                        borderColor: '#dc3545',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: false
                    },
                    {
                        label: 'Diastolic BP',
                        data: diastolicData,
                        borderColor: '#198754',
                        backgroundColor: 'rgba(25, 135, 84, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Blood Pressure Trends',
                        color: '#f8f9fa',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        labels: {
                            color: '#f8f9fa'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        suggestedMin: 60,
                        suggestedMax: 180
                    }
                }
            }
        });
    }
    
    // Function to create a weight trend chart
    function createWeightChart(canvasId, labels, weightData) {
        if (!document.getElementById(canvasId)) return;
        
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Weight (kg)',
                        data: weightData,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Weight Trends',
                        color: '#f8f9fa',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        labels: {
                            color: '#f8f9fa'
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    // Function to create a lab results trend chart
    function createLabTrendChart(canvasId, labels, values, testName, unit, referenceMin, referenceMax) {
        if (!document.getElementById(canvasId)) return;
        
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        // Create dataset with conditional point colors based on reference range
        const pointColors = values.map(value => {
            if (referenceMin !== null && value < referenceMin) return '#dc3545'; // Below range
            if (referenceMax !== null && value > referenceMax) return '#dc3545'; // Above range
            return '#198754'; // Within range
        });
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `${testName} (${unit})`,
                        data: values,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: false,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: pointColors
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: `${testName} Trends`,
                        color: '#f8f9fa',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        labels: {
                            color: '#f8f9fa'
                        }
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                yMin: referenceMin,
                                yMax: referenceMin,
                                borderColor: 'rgba(255, 193, 7, 0.5)',
                                borderWidth: 2,
                                label: {
                                    content: 'Min',
                                    enabled: true,
                                    position: 'left'
                                }
                            },
                            line2: {
                                type: 'line',
                                yMin: referenceMax,
                                yMax: referenceMax,
                                borderColor: 'rgba(255, 193, 7, 0.5)',
                                borderWidth: 2,
                                label: {
                                    content: 'Max',
                                    enabled: true,
                                    position: 'left'
                                }
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        ticks: {
                            color: '#f8f9fa'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    // Function to create a screening compliance chart
    function createScreeningComplianceChart(canvasId, labels, data) {
        if (!document.getElementById(canvasId)) return;
        
        const ctx = document.getElementById(canvasId).getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [
                    {
                        data: data,
                        backgroundColor: [
                            '#198754', // Completed
                            '#dc3545', // Overdue
                            '#ffc107'  // Due soon
                        ],
                        borderWidth: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Screening Compliance',
                        color: '#f8f9fa',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#f8f9fa'
                        }
                    }
                }
            }
        });
    }
    
    // Initialize charts if data is available via data attributes
    const chartElements = document.querySelectorAll('[data-chart-type]');
    chartElements.forEach(element => {
        const chartType = element.getAttribute('data-chart-type');
        const canvasId = element.id;
        
        if (chartType === 'bp-trend') {
            const labels = JSON.parse(element.getAttribute('data-labels'));
            const systolicData = JSON.parse(element.getAttribute('data-systolic'));
            const diastolicData = JSON.parse(element.getAttribute('data-diastolic'));
            createVitalsChart(canvasId, labels, systolicData, diastolicData);
        }
        else if (chartType === 'weight-trend') {
            const labels = JSON.parse(element.getAttribute('data-labels'));
            const weightData = JSON.parse(element.getAttribute('data-weight'));
            createWeightChart(canvasId, labels, weightData);
        }
        else if (chartType === 'lab-trend') {
            const labels = JSON.parse(element.getAttribute('data-labels'));
            const values = JSON.parse(element.getAttribute('data-values'));
            const testName = element.getAttribute('data-test-name');
            const unit = element.getAttribute('data-unit');
            const referenceMin = parseFloat(element.getAttribute('data-ref-min'));
            const referenceMax = parseFloat(element.getAttribute('data-ref-max'));
            createLabTrendChart(canvasId, labels, values, testName, unit, referenceMin, referenceMax);
        }
        else if (chartType === 'screening-compliance') {
            const labels = JSON.parse(element.getAttribute('data-labels'));
            const data = JSON.parse(element.getAttribute('data-values'));
            createScreeningComplianceChart(canvasId, labels, data);
        }
    });
});
