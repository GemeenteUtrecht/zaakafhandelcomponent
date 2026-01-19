import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'gu-progress-bar',
  templateUrl: './progress-bar.component.html',
  styleUrls: ['./progress-bar.component.scss']
})
export class ProgressBarComponent implements OnInit {

  @Input() progress: number;
  @Input() endDate: string;
  @Input() finished: boolean;
  roundedNumber: string;
  total = 100;

  constructor() { }

  ngOnInit(): void {
    this.roundedNumber = this.progress.toFixed(0);
    this.setProgress();
  }

  setProgress() {
    //if we don't have progress, set it to 0.
    if(!this.progress) {
      this.progress = 0;
    }
    //if we don't have a total aka no requirement, it's 100%.
    if(this.total === 0) {
      this.total = this.progress;
    } else if(!this.total) {
      this.total = 100;
    }
    //if the progress is greater than the total, it's also 100%.
    if(this.progress > this.total) {
      this.progress = 100;
      this.total = 100;
    }
    this.progress = (this.progress / this.total) * 100;
  }
}
