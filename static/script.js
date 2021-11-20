async function getData() {
    const now = new Date();
    const startTime = `2020-${(''+(now.getMonth()+1)).padStart(2, '0')}-${(''+now.getDate()).padStart(2, '0')}`;
    const inOneWeek = new Date(now.getTime() + 24*60*60*7*1000);
    const endTime = `2020-${(''+(inOneWeek.getMonth()+1)).padStart(2, '0')}-${(''+inOneWeek.getDate()).padStart(2, '0')}`;
    const response = await fetch(`/stats/3?start=${startTime}&end=${endTime}`)
    const body = await response.json()
    return body
}

function getDataset(percentageConsumingLess) {
    const colors = [
        'rgba(255, 200, 200, 0.4)',
        'rgba(255, 100, 100, 0.4)',
        'rgba(255, 50, 50, 0.4)'
    ]

    const pointerThickness = 0.02

    if (0.0 <= percentageConsumingLess && percentageConsumingLess < 1/3) {
        const pos = percentageConsumingLess
        return [
            {color: colors[0], value: pos},
            {color: 'red',     value: pointerThickness},
            {color: colors[0], value: 1/3 - pos - pointerThickness},
            {color: colors[1], value: 1/3},
            {color: colors[2], value: 1/3},
        ]
    } else if (1/3 <= percentageConsumingLess && percentageConsumingLess < 2/3) {
        const pos = percentageConsumingLess - 1/3
        return [
            {color: colors[0], value: 1/3},
            {color: colors[1], value: pos},
            {color: 'red',     value: pointerThickness},
            {color: colors[1], value: 1/3 - pos - pointerThickness},
            {color: colors[2], value: 1/3},
        ]
    } else if (2/3 <= percentageConsumingLess && percentageConsumingLess <= 1) {
        const pos = percentageConsumingLess - 2/3
        return [
            {color: colors[0], value: 1/3},
            {color: colors[1], value: 1/3},
            {color: colors[2], value: pos},
            {color: 'red',     value: pointerThickness},
            {color: colors[2], value: 1/3 - pos - 0.1},
        ]
    }
}

function instantiateChart(id, percentageConsumingLess, actualConsumption) {
    const ctx = document.getElementById(id).getContext('2d')

    const dataset = getDataset(percentageConsumingLess)

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: dataset.map(item => item.value),
                backgroundColor: dataset.map(item => item.color)
            }]
        },
        options: {
            rotation: 180,
            borderWidth: 0,
            events: [],
            plugins: {
                title: {
                    display: true,
                    text: actualConsumption.toFixed(2) + ' liters',
                }
            }
        }
    })
}

async function init() {
    const data = await getData()
    const total = 
        (data.apartment_stats.total_consumption
            - data.smallest_apartment_total_consumption.total_consumption) /
        (data.largest_apartment_total_consumption.total_consumption
            - data.smallest_apartment_total_consumption.total_consumption)
    const manual = 
        (data.apartment_device_stats.manual.total_consumption
            - data.smallest_apartment_device_consumption.manual.total_consumption) /
        (data.largest_apartment_device_consumption.manual.total_consumption
            - data.smallest_apartment_device_consumption.manual.total_consumption)
    const automatic = 
        (data.apartment_device_stats.automatic.total_consumption
            - data.smallest_apartment_device_consumption.automatic.total_consumption) /
        (data.largest_apartment_device_consumption.automatic.total_consumption
            - data.smallest_apartment_device_consumption.automatic.total_consumption)
    instantiateChart('consumptionTotal', total, data.apartment_stats.total_consumption)
    instantiateChart('consumptionShower', manual, data.apartment_device_stats.manual.total_consumption)
    instantiateChart('consumptionAppliances', automatic, data.apartment_device_stats.automatic.total_consumption)
}

init()
