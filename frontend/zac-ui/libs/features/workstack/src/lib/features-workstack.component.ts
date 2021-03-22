import { Component, OnInit } from '@angular/core';
import { FeaturesWorkstackService } from './features-workstack.service';
import { tabs, Tab } from './constants/tabs';

@Component({
  selector: 'gu-features-workstack',
  templateUrl: './features-workstack.component.html',
  styleUrls: ['./features-workstack.component.scss']
})

export class FeaturesWorkstackComponent implements OnInit {

  tabs: Tab[] = tabs;

  constructor(private workstackService: FeaturesWorkstackService) { }

  ngOnInit(): void {
    this.fetchWorkstack();
  }

  fetchWorkstack() {
    this.workstackService.getWorkstack(tabs).subscribe(res => {
      console.log(res);
    });
  }

}
