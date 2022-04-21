import {
  Component,
  ViewEncapsulation,
  ElementRef,
  Input,
  OnInit,
  OnDestroy,
  Output,
  EventEmitter
} from '@angular/core';

import { ModalService } from "./modal.service";

@Component({
  selector: 'gu-modal',
  templateUrl: 'modal.component.html',
  styleUrls: ['modal.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class ModalComponent implements OnInit, OnDestroy {
  @Input() id: string;
  @Input() closeIcon: boolean;
  @Input() expandVertical = false
  @Input() title: string;
  @Input() size: 'small' | 'medium' | 'huge' = 'medium';
  @Input() type: 'center' | 'right' = 'center';

  @Output() onClose: EventEmitter<boolean> = new EventEmitter<boolean>();

  private element: any;

  constructor(private modalService: ModalService, private el: ElementRef) {
    this.element = el.nativeElement;
  }

  ngOnInit(): void {
    // ensure id attribute exists
    if (!this.id) {
      console.error('modal must have an id');
      return;
    }

    // move element to bottom of page (just before </body>) so it can be displayed above everything else
    document.body.appendChild(this.element);

    // close modal on background click
    this.element.addEventListener('click', el => {
      if (el.target.className === 'gu-modal') {
        this.close();
      }
    });

    // add self (this modal instance) to the modal service so it's accessible from controllers
    this.modalService.add(this);
  }

  // remove self from modal service when component is destroyed
  ngOnDestroy(): void {
    this.modalService.remove(this.id);
    this.element.remove();
  }

  // open modal
  open(): void {
    this.element.style.display = 'block';
    this.element.classList.add('gu-modal-open');
    document.body.classList.add('gu-modal-open');
  }

  // close modal
  close(): void {
    this.element.style.display = 'none';
    this.element.classList.remove('gu-modal-open');
    document.body.classList.remove('gu-modal-open');
    this.onClose.emit(true);
  }
}
