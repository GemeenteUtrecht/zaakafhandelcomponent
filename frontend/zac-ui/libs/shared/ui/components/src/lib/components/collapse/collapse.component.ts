import {Component, Input} from "@angular/core";


/**
 * <gu-collapse [collapsed]="collapsed"></gu-collapse>
 *
 * Shows a collapsible panel.
 */
@Component({
  selector: 'gu-collapse',
  templateUrl: './collapse.component.html',
  styleUrls: ['./collapse.component.scss']
})
export class CollapseComponent {
  @Input() collapsed: boolean = !window.matchMedia('(min-width: 768px)').matches;

  //
  // Events.
  //

  /**
   * Gets called when the toggle button is clicked.
   * @param {PointerEvent} e
   */
  onClick(e) {
    e.preventDefault();
    this.collapsed = !this.collapsed;
  }
}
