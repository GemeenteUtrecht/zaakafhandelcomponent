import { Component, OnInit } from '@angular/core';
import { FeaturesWorkstackService } from './features-workstack.service';
import { tabs, Tab } from './constants/tabs';
import { tableHead, tableHeadMapping } from './constants/zaken-tablehead';
import { RowData, Zaak, Table, UserTask, UserTaskZaak, Task } from '@gu/models';
import { AccessRequests } from './models/access-request';
import { AdHocActivities } from './models/activities';

@Component({
  selector: 'gu-features-workstack',
  templateUrl: './features-workstack.component.html',
  styleUrls: ['./features-workstack.component.scss'],
})
export class FeaturesWorkstackComponent implements OnInit {
  tabs: Tab[] = tabs;

  allData: any;
  zakenData: Zaak[];
  taskData: UserTask[];
  activitiesData: AdHocActivities[];
  accessRequestData: AccessRequests[];

  zakenTableData: Table = new Table(tableHead, []);

  isLoading: boolean;

  currentActiveTab: string;

  constructor(private workstackService: FeaturesWorkstackService) {}

  ngOnInit(): void {
    this.fetchWorkstack();
  }

  fetchWorkstack() {
    this.isLoading = true;
    this.workstackService.getWorkstack(tabs).subscribe(
      (res) => {
        this.allData = res;
        this.zakenData = res[0];
        this.taskData = res[1];
        this.activitiesData = res[2];
        this.accessRequestData = res[3];
        this.zakenTableData.bodyData = this.formatZakenTableData(
          this.zakenData
        );
        this.isLoading = false;
      },
      (error) => {
        console.log(error);
        this.isLoading = false;
      }
    );
  }

  fetchZaken(sortValue) {
    this.workstackService
      .getWorkstackZaken(tableHeadMapping[sortValue.value], sortValue.order)
      .subscribe(
        (res) => {
          this.zakenData = res;
          this.zakenTableData.bodyData = this.formatZakenTableData(
            this.zakenData
          );
        },
        (error) => {
          console.log(error);
        }
      );
  }

  reloadWorkstack(tab) {
    this.fetchWorkstack();
    this.currentActiveTab = tab;
  }

  formatZakenTableData(data: Zaak[]): RowData[] {
    return data.map((element) => {
      const zaakUrl = `/ui/zaken/${element.bronorganisatie}/${element.identificatie}`;

      const cellData: RowData = {
        cellData: {
          link: {
            type: 'link',
            label: element.identificatie,
            url: zaakUrl,
          },
          zaaktype: element.zaaktype.omschrijving,
          startdate: element.startdatum,
          deadline: element.deadline,
          trust: element.vertrouwelijkheidaanduiding,
        },
      };
      return cellData;
    });
  }

  createRouteLink(zaak: UserTaskZaak, task: Task) {
    if (task.hasForm) {
      return `/ui/zaken/${zaak.bronorganisatie}/${zaak.identificatie}?user-task=${task.id}`;
    } else {
      return task.executeUrl;
    }
  }

  createActivityLink(zaak) {
    return `/ui/zaken/${zaak.bronorganisatie}/${zaak.identificatie}?activities=true`;
  }
}
