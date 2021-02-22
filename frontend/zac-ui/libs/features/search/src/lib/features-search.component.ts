import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FeaturesSearchService } from './features-search.service';
import { Result} from '../models/zaaktype';
import { ZaaktypeEigenschap } from '../models/zaaktype-eigenschappen';

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss']
})
export class FeaturesSearchComponent implements OnInit {

  searchForm: FormGroup

  zaaktypenData: Result[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[];

  selectedPropertyValue: ZaaktypeEigenschap;

  constructor(
    private fb: FormBuilder,
    private searchService: FeaturesSearchService
  ) { }

  ngOnInit(): void {
    this.searchForm = this.fb.group({
      zaaknummer: [''],
      omschrijving: [''],
      eigenschapwaarde: ['']
    })
    this.fetchZaaktypen();
  }

  fetchZaaktypen() {
    this.searchService.getZaaktypen().subscribe(res => {
      this.zaaktypenData = res.results;
    })
  }

  onZaaktypeSelect(zaaktype: Result) {
    if (zaaktype) {
      const catalogus = zaaktype.catalogus;
      const omschrijving = zaaktype.omschrijving;

      this.searchService.getZaaktypeEigenschappen(catalogus, omschrijving).subscribe(res => {
        this.zaaktypeEigenschappenData = res;
      })
    } else {
      this.zaaktypeEigenschappenData = null;
    }
  }

  onPropertySelect(property: ZaaktypeEigenschap) {
    this.selectedPropertyValue = property;
  }

  submitForm() {

  }

  addPropertyFormControls() {
    this.zaaktypeEigenschappenData.forEach(property => {

    })
  }

  get zaaknummer(): FormControl {
    return this.searchForm.get('zaaknummer') as FormControl;
  };

  get omschrijving(): FormControl {
    return this.searchForm.get('omschrijving') as FormControl;
  };

  get eigenschapwaarde(): FormControl {
    return this.searchForm.get('eigenschapwaarde') as FormControl;
  };
}
