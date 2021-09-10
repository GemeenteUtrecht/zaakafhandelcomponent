import {DOCUMENT} from '@angular/common';
import {AfterViewInit, Component, Inject, Input, OnInit, Renderer2, ViewChild} from '@angular/core';

@Component({
    selector: 'gu-features-contezza-document-search',
    templateUrl: './features-contezza-document-search.component.html',
    styleUrls: ['./features-contezza-document-search.component.scss'],
})
export class FeaturesContezzaDocumentSearchComponent implements OnInit, AfterViewInit {
    @Input() bronorganisatie: string;

    @Input() username: string;
    @Input() password: string;

    @Input() mode: string;
    @Input() rootfolder: string;
    @Input() zaaktypeurl = 'http://openzaak.local:8000/catalogi/api/v1/zaaktypen/7dc9fdc5-b2f8-465f-9584-8f59ca84488b';

    @ViewChild('wrapper') wrapper;

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


    /**
     * A lifecycle hook that is called after Angular has fully initialized a component's view. Define an ngAfterViewInit()
     * method to handle any additional initialization tasks.
     */
    ngAfterViewInit() {
        if(!this.wrapper?.nativeElement) {
            return;
        }

        const cdl = this.renderer2.createElement('contezza-documentlist');
        cdl.setAttribute('bronorganisatie', this.bronorganisatie)
        cdl.setAttribute('username', this.username)
        cdl.setAttribute('password', this.password)
        cdl.setAttribute('mode', 'search')
        cdl.setAttribute('zaaktypeurl', this.zaaktypeurl)
        this.renderer2.appendChild(this.wrapper.nativeElement, cdl);

        cdl.addEventListener('callbackurl', this.onCallbackUrl.bind(this));
    }

    //
    // Events.
    //

    onCallbackUrl(event: Event) {
        console.log('onCallbackUrl', event);
    };
}
