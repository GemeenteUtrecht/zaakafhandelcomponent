import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent implements OnInit {

  constructor() { }

  @Input() expandable = true;
  @Input() headData: any[] = ['Adviseur', 'Gedaan op'];
  @Input() elementData: any[] = [
    {
      cellData: {
        advisor: 'John Doe',
        created: '3 november 2020 12:24'
      },
      expandData: 'Proin quis massa a quam consequat cursus fringilla vel purus. Nunc at felis feugiat, aliquet massa eu, porta mauris. Sed ac turpis at dolor consequat venenatis. Aenean sed blandit leo. Suspendisse dignissim arcu tortor, in faucibus arcu fringilla vitae. Maecenas at velit quis elit tincidunt pellentesque in id erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum bibendum ut erat non vehicula. Quisque at lacus nec sem pulvinar interdum.\n' +
        '\n'
    },
    {
      cellData: {
        advisor: 'John Doe',
        created: '3 november 2020 12:24'
      },
      expandData: 'Proin quis massa a quam consequat cursus fringilla vel purus. Nunc at felis feugiat, aliquet massa eu, porta mauris. Sed ac turpis at dolor consequat venenatis. Aenean sed blandit leo. Suspendisse dignissim arcu tortor, in faucibus arcu fringilla vitae. Maecenas at velit quis elit tincidunt pellentesque in id erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum bibendum ut erat non vehicula. Quisque at lacus nec sem pulvinar interdum.\n' +
        '\n'
    },
    {
      cellData: {
        advisor: 'John Doe',
        created: '3 november 2020 12:24'
      },
      expandData: 'Proin quis massa a quam consequat cursus fringilla vel purus. Nunc at felis feugiat, aliquet massa eu, porta mauris. Sed ac turpis at dolor consequat venenatis. Aenean sed blandit leo. Suspendisse dignissim arcu tortor, in faucibus arcu fringilla vitae. Maecenas at velit quis elit tincidunt pellentesque in id erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum bibendum ut erat non vehicula. Quisque at lacus nec sem pulvinar interdum.\n' +
        '\n'
    },
    {
      cellData: {
        advisor: 'John Doe',
        created: '3 november 2020 12:24'
      },
      expandData: 'Proin quis massa a quam consequat cursus fringilla vel purus. Nunc at felis feugiat, aliquet massa eu, porta mauris. Sed ac turpis at dolor consequat venenatis. Aenean sed blandit leo. Suspendisse dignissim arcu tortor, in faucibus arcu fringilla vitae. Maecenas at velit quis elit tincidunt pellentesque in id erat. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Vestibulum bibendum ut erat non vehicula. Quisque at lacus nec sem pulvinar interdum.\n' +
        '\n'
    }
  ]

  ngOnInit(): void {
  }

  expandRow(event) {
    const arrow = event.target;
    const parentRow = event.currentTarget.parentElement.parentElement;
    const childRow = parentRow.nextElementSibling;

    if (!childRow.classList.contains('child-row--expanded')) {
      childRow.classList.add('child-row--expanded');
    } else {
      childRow.classList.remove('child-row--expanded');
    }

    this.rotateArrow(arrow);
  }

  rotateArrow(arrow) {
    if (!arrow.classList.contains('arrow--rotated')) {
      arrow.classList.add('arrow--rotated');
    } else {
      arrow.classList.remove('arrow--rotated');
    }
  }

}
