import { Component, OnInit, ViewChild } from '@angular/core';
import { ChartComponent, NgApexchartsModule } from 'ng-apexcharts';
import { ChartConfiguration, ChartType as chartJsChartType } from 'chart.js';
import {
  ApexNonAxisChartSeries,
  ApexResponsive,
  ApexChart,
  ApexAxisChartSeries,
  ApexTitleSubtitle,
  ApexXAxis,
  ApexFill,
  ApexStroke,
  ApexLegend,
  ApexPlotOptions,
  ApexDataLabels,
  ApexTooltip,
  ApexYAxis,
  ApexGrid,
  ApexMarkers,
} from 'ng-apexcharts';
import { NgbProgressbar } from '@ng-bootstrap/ng-bootstrap';
import { BaseChartDirective } from 'ng2-charts';
import { RouterLink } from '@angular/router';
export type circleChartOptions = {
  series?: ApexNonAxisChartSeries;
  chart?: ApexChart;
  labels?: string[];
  colors?: string[];
  legend?: ApexLegend;
  plotOptions?: ApexPlotOptions;
  responsive?: ApexResponsive[];
};
export type radarChartOptions = {
  series?: ApexAxisChartSeries;
  chart?: ApexChart;
  title?: ApexTitleSubtitle;
  stroke?: ApexStroke;
  fill?: ApexFill;
  markers?: ApexMarkers;
  xaxis?: ApexXAxis;
};
export type areaChartOptions = {
  series?: ApexAxisChartSeries;
  chart?: ApexChart;
  xaxis?: ApexXAxis;
  stroke?: ApexStroke;
  grid?: ApexGrid;
  tooltip?: ApexTooltip;
  legend?: ApexLegend;
  dataLabels?: ApexDataLabels;
};
export type pieChartOptions = {
  series?: ApexNonAxisChartSeries;
  chart?: ApexChart;
  legend?: ApexLegend;
  dataLabels?: ApexDataLabels;
  responsive?: ApexResponsive[];
  labels?: string[];
};
export type avgLecChartOptions = {
  series?: ApexAxisChartSeries;
  chart?: ApexChart;
  xaxis?: ApexXAxis;
  stroke?: ApexStroke;
  dataLabels?: ApexDataLabels;
  markers?: ApexMarkers;
  colors?: string[];
  yaxis?: ApexYAxis;
  grid?: ApexGrid;
  tooltip?: ApexTooltip;
  legend?: ApexLegend;
  fill?: ApexFill;
  title?: ApexTitleSubtitle;
};

@Component({
    selector: 'app-chart-widget',
    templateUrl: './chart-widget.component.html',
    styleUrls: ['./chart-widget.component.sass'],
    imports: [RouterLink, NgApexchartsModule, BaseChartDirective, NgbProgressbar]
})
export class ChartWidgetComponent implements OnInit {
  public radarChartOptions!: Partial<radarChartOptions>;
  public circleChartOptions!: Partial<circleChartOptions>;
  public areaChartOptions!: Partial<areaChartOptions>;
  public pieChartOptions!: Partial<pieChartOptions>;
  public avgLecChartOptions!: Partial<avgLecChartOptions>;
  constructor() {
    //constructor
  }
  @ViewChild('chart', { static: true }) chart!: ChartComponent;

  // Area chart start

  public areaChartData: ChartConfiguration['data'] = {
    datasets: [
      {
        label: 'Foods',
        data: [460, 458, 330, 502, 430, 610, 488],
        borderWidth: 2,
        pointStyle: 'circle',
        pointBorderColor: 'transparent',
        fill: 'origin',
        backgroundColor: 'rgba(145,141,197,.8)',
        borderColor: 'transparent',
        pointBorderWidth: 0,
        pointRadius: 1.5,
        pointBackgroundColor: 'transparent',
        pointHoverBackgroundColor: 'rgba(63,82,227,.8)',
      },
      {
        label: 'Electronics',
        data: [390, 600, 390, 280, 600, 430, 638],
        borderWidth: 2,
        pointStyle: 'circle',
        pointRadius: 3,
        pointBorderColor: 'transparent',
        fill: 'origin',

        backgroundColor: 'rgba(58,184,214,.7)',
        borderColor: 'transparent',
        pointBorderWidth: 0,
        pointBackgroundColor: 'transparent',
        pointHoverBackgroundColor: 'rgba(254,86,83,.8)',
      },
    ],
    labels: [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
    ],
  };

  public areaChart: ChartConfiguration['options'] = {
    elements: {
      line: {
        tension: 0.5,
      },
    },
    scales: {
      // We use this empty structure as a placeholder for dynamic theming.
      y: {
        position: 'left',
        ticks: {
          color: '#9aa0ac', // Font Color
        },
      },
      x: {
        ticks: {
          color: '#9aa0ac', // Font Color
        },
      },
    },

    plugins: {
      legend: { display: true },
    },
  };

  public areaChartType: chartJsChartType = 'line';

  // area chart end

  // Line chert start

  public lineChartData: ChartConfiguration['data'] = {
    datasets: [
      {
        label: 'Google',
        data: [290, 358, 220, 402, 440, 510, 688],
        borderWidth: 2,
        backgroundColor: 'transparent',
        borderColor: 'rgba(254,86,83,.7)',
        pointBackgroundColor: 'transparent',
        pointBorderColor: 'transparent',
        pointRadius: 4,
      },
      {
        label: 'Facebook',
        data: [450, 258, 390, 162, 650, 570, 438],
        borderWidth: 2,
        backgroundColor: 'transparent',
        borderColor: 'rgba(63,82,227,.8)',
        pointBackgroundColor: 'transparent',
        pointBorderColor: 'transparent',
        pointRadius: 4,
      },
    ],
    labels: [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday',
    ],
  };

  public lineChartOptions: ChartConfiguration['options'] = {
    elements: {
      line: {
        tension: 0.5,
      },
    },
    scales: {
      y: {
        position: 'left',
        ticks: {
          color: '#9aa0ac', // Font Color
        },
      },
      x: {
        ticks: {
          color: '#9aa0ac', // Font Color
        },
      },
    },

    plugins: {
      legend: { display: true },
    },
  };

  public lineChartType: chartJsChartType = 'line';

  // Line chart end

  ngOnInit(): void {
    this.pieChart();
    this.radarChart();
    this.chartArea();
    this.initChartReport4();
    this.initChartReport3();
  }

  private pieChart() {
    this.circleChartOptions = {
      series: [76, 67, 61, 90],
      chart: {
        height: 275,
        type: 'radialBar',
      },
      plotOptions: {
        radialBar: {
          offsetY: 0,
          startAngle: 0,
          endAngle: 270,
          hollow: {
            margin: 5,
            size: '30%',
            background: 'transparent',
            image: undefined,
          },
          dataLabels: {
            name: {
              show: false,
            },
            value: {
              show: false,
            },
          },
        },
      },
      colors: ['#FF4560', '#775DD0', '#00E396', '#FEB019'],
      labels: ['Vimeo', 'Messenger', 'Facebook', 'LinkedIn'],
      legend: {
        show: true,
        floating: true,
        fontSize: '12px',
        position: 'left',
        offsetX: 10,
        offsetY: 10,
        labels: {
          useSeriesColors: true,
        },
        itemMargin: {
          horizontal: 3,
        },
      },
      responsive: [
        {
          breakpoint: 480,
          options: {
            legend: {
              show: false,
            },
          },
        },
      ],
    };
  }
  private radarChart() {
    this.radarChartOptions = {
      series: [
        {
          name: 'Series Blue',
          data: [80, 50, 30, 40, 100, 20],
        },
        {
          name: 'Series Green',
          data: [20, 30, 40, 80, 20, 80],
        },
        {
          name: 'Series Orange',
          data: [44, 76, 78, 13, 43, 10],
        },
      ],
      chart: {
        height: 270,
        type: 'radar',
        dropShadow: {
          enabled: true,
          blur: 1,
          left: 1,
          top: 1,
        },
      },
      stroke: {
        width: 0,
      },
      fill: {
        opacity: 0.4,
      },
      markers: {
        size: 0,
      },
      xaxis: {
        categories: ['2011', '2012', '2013', '2014', '2015', '2016'],
      },
    };
  }
  private chartArea() {
    this.areaChartOptions = {
      chart: {
        height: 270,
        type: 'area',
        foreColor: '#9aa0ac',
        toolbar: {
          show: false,
        },
      },
      legend: {
        show: false,
      },
      dataLabels: {
        enabled: false,
      },
      stroke: {
        curve: 'smooth',
      },
      series: [
        {
          name: 'series1',
          data: [31, 40, 28, 51, 42],
        },
        {
          name: 'series2',
          data: [11, 32, 45, 32, 34],
        },
      ],
      xaxis: {
        type: 'datetime',
        categories: ['1990', '1991', '1992', '1993', '1994'],
      },
      tooltip: {
        x: {
          format: 'dd/MM/yy HH:mm',
        },
      },
    };
  }
  private initChartReport4() {
    this.avgLecChartOptions = {
      series: [
        {
          name: 'Avg. Lecture',
          data: [65, 72, 62, 73, 66, 74, 63, 67],
        },
      ],
      chart: {
        height: 350,
        type: 'line',
        foreColor: '#9aa0ac',
        dropShadow: {
          enabled: true,
          color: '#000',
          top: 18,
          left: 7,
          blur: 10,
          opacity: 0.2,
        },
        toolbar: {
          show: false,
        },
      },
      stroke: {
        curve: 'smooth',
      },
      xaxis: {
        categories: ['Jan', 'Feb', 'March', 'Apr', 'May', 'Jun', 'July', 'Aug'],
        title: {
          text: 'Weekday',
        },
      },
      yaxis: {
        title: {
          text: 'Avg. Lecture',
        },
      },
      fill: {
        type: 'gradient',
        gradient: {
          shade: 'dark',
          gradientToColors: ['#35fdd8'],
          shadeIntensity: 1,
          type: 'horizontal',
          opacityFrom: 1,
          opacityTo: 1,
          stops: [0, 100, 100, 100],
        },
      },
      markers: {
        size: 4,
        colors: ['#FFA41B'],
        strokeColors: '#fff',
        strokeWidth: 2,
        hover: {
          size: 7,
        },
      },
      tooltip: {
        theme: 'dark',
        marker: {
          show: true,
        },
        x: {
          show: true,
        },
      },
    };
  }
  private initChartReport3() {
    this.pieChartOptions = {
      series: [44, 55, 13, 43, 22],
      chart: {
        type: 'donut',
        width: 200,
      },
      legend: {
        show: false,
      },
      dataLabels: {
        enabled: false,
      },
      labels: ['Science', 'Mathes', 'Economics', 'History', 'Music'],
      responsive: [
        {
          breakpoint: 480,
          options: {},
        },
      ],
    };
  }
}
