import {DOCUMENT} from '@angular/common';
import {Component, Inject, OnInit, Renderer2} from '@angular/core';

@Component({
    selector: 'gu-features-contezza-document-search',
    templateUrl: './features-contezza-document-search.component.html',
    styleUrls: ['./features-contezza-document-search.component.scss'],
})
export class FeaturesContezzaDocumentSearchComponent implements OnInit {
    /**
     * Constructor method.
     * @param {Renderer2} renderer2
     * @param {Document} document
     */
    constructor(private renderer2: Renderer2, @Inject(DOCUMENT) private document: Document) {
    }

    //
    // Angular lifecycle.
    //

    /**
     * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
     * ngOnInit() method to handle any additional initialization tasks.
     */
    ngOnInit() {
        const script = this.renderer2.createElement('script');
        script.src = '/ui/assets/contezza-documentlist.js';
        this.renderer2.appendChild(this.document.body, script);
    }
}
