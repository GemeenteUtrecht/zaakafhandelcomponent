import {DOCUMENT} from '@angular/common';
import {AfterViewInit, Component, ElementRef, Inject, Input, OnInit, Renderer2, ViewChild, ViewEncapsulation} from '@angular/core';

@Component({
    selector: 'gu-features-contezza-document-search',
    templateUrl: './features-contezza-document-search.component.html',
    styleUrls: ['./features-contezza-document-search.component.scss'],
})
export class FeaturesContezzaDocumentSearchComponent implements OnInit, AfterViewInit {
    @Input()
    bronorganisatie: string;

    @Input()
    mode: string;

    @Input()
    rootfolder: string;

    @Input()
    zaaktypeurl;

    @ViewChild('wrapper', { static: false })
    wrapper: ElementRef;

    /**
     * Constructor method.
     * @param {Renderer2} renderer2
     * @param {Document} document
     */
    constructor(private renderer2: Renderer2, @Inject(DOCUMENT) private document: Document) {}

    //
    // Angular lifecycle.
    //

    /**
     * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
     * ngOnInit() method to handle any additional initialization tasks.
     */
    ngOnInit() {
        if (this.zaaktypeurl && this.zaaktypeurl.includes('utrechtproeftuin')) {
          const urlParts = this.zaaktypeurl.split('://');
          const typeParts = urlParts[1].split('/').slice(1);
          this.zaaktypeurl = `${urlParts[0]}://openzaak.cg-intern.ont.utrecht.nl/${typeParts.join('/')}`;
        }

        const script = this.renderer2.createElement('script');
        script.src = '/ui/assets/contezza-zac-doclib.js';
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

        const cdl = this.renderer2.createElement('contezza-zac-doclib');
        cdl.setAttribute('bronorganisatie', this.bronorganisatie)
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
