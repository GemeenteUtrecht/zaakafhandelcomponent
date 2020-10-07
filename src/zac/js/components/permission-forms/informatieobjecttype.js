import React from 'react';
import {Select} from '../forms/Select';
import {CheckboxInput, HiddenInput} from '../forms/Inputs';
import {ManagementForm} from "../formsets/ManagementForm";
import PropTypes from "prop-types";


class InformatieobjecttypePermissionForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            displayFormset: false,
            currentCatalog: '',
            currentOmschrijvingen: [],
        };

        this.getCatalogSelect = this.getCatalogSelect.bind(this);
        this.getFormSet = this.getFormSet.bind(this);
        this.onCatalogChange = this.onCatalogChange.bind(this);
        this.retrieveOmschrijvingen = this.retrieveOmschrijvingen.bind(this);
    }

    componentDidMount() {
        if (this.props.initialData.catalogus !== '') {
            const omschrijvingen = this.retrieveOmschrijvingen(this.props.initialData.catalogus);
            this.setState({
                currentCatalog: this.props.initialData.catalogus,
                displayFormset: true,
                currentOmschrijvingen: omschrijvingen,
            });
        }
    }

    getCatalogSelect() {
        const catalog_choices = [['', '------']].concat(this.props.catalogData);

        return (
            <Select
                name='informatieobjecttype_catalogus'
                id='id_informatieobjecttype_catalogus'
                label='Catalogus'
                helpText='Select the catalog containing the desired informatieobjecttype'
                choices={catalog_choices}
                value={this.state.currentCatalog}
                onChange={this.onCatalogChange}
            />
        );
    }

    retrieveOmschrijvingen(chosenCatalogUrl){
        for ( const catalogUrl in this.props.informatieobjecttypeData){
            if (catalogUrl === chosenCatalogUrl) {
                return this.props.informatieobjecttypeData[catalogUrl];
            }
        }
        return [];
    }

    onCatalogChange(event) {

        this.setState({
            currentCatalog: event.target.value,
            displayFormset: event.target.value !== '',
            currentOmschrijvingen: this.retrieveOmschrijvingen(event.target.value)
        });
    }

    getFormSet() {
        if (this.state.displayFormset) {
            const forms = this.state.currentOmschrijvingen.map((value, index) => {
                const checked = value in this.props.initialData;
                const max_va = (value in this.props.initialData) ? this.props.initialData[value][0] : "openbaar";
                const id = (value in this.props.initialData) ? this.props.initialData[value][1] : null;
                return (
                    <InformatieobjecttypeField
                        catalogus={this.state.currentCatalog}
                        checked={checked}
                        max_va={max_va}
                        omschrijving={value}
                        id={id}
                    />
                );
            });

            return (
                <React.Fragment>
                    <h4>Select informatieobjecttypes to modify</h4>
                    <ManagementForm
                        prefix={ this.props.configuration.prefix }
                        initial={ this.props.configuration.initial }
                        total={ 1 }
                        minNum={ this.props.configuration.minNum }
                        maxNum={ this.props.configuration.maxNum }
                    />

                    <ul className="checkbox-select">
                        { forms }
                    </ul>
                </React.Fragment>
            );
        }
    }

    render() {
        return (
            <React.Fragment>
                {this.getCatalogSelect()}
                {this.getFormSet()}
            </React.Fragment>
        );
    }
}

class InformatieobjecttypeField extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            checked: this.props.checked,
            max_va: this.props.max_va,
            id: this.props.id
        };

        this.onCheckChange = this.onCheckChange.bind(this);
        this.onVAChange = this.onVAChange.bind(this);
    }

    onCheckChange(event) {
        this.setState(state => ({checked: !state.checked}));
    }

    onVAChange(event) {
        this.setState({max_va: event.target.value});
    }

    render(){
        return (
            <div className='form__field-group informatieobjecttypen-choices'>
                <CheckboxInput
                    name={this.props.omschrijving + '-modify'}
                    id={'id-' + this.props.omschrijving + '-modify'}
                    checked={this.state.checked}
                    initial={this.state.checked}
                    value={this.state.checked}
                    onChange={this.onCheckChange}
                />
                <label>{this.props.omschrijving}</label>
                <HiddenInput name={this.props.omschrijving+'-omschrijving'} value={ this.props.omschrijving } />
                <HiddenInput name={this.props.omschrijving+'-id'} value={ this.props.id } />
                <Select
                    name={this.props.omschrijving + '-max_va'}
                    id={'id-' + this.props.omschrijving + '-max_va'}
                    choices={[
                        ['openbaar', 'Openbaar'],
                        ['beperkt_openbaar', 'Beperkt openbaar'],
                        ['intern', 'Intern'],
                        ['zaakvertrouwelijk', 'Zaakvertrouwelijk'],
                        ['vertrouwelijk', 'Vertrouwelijk'],
                        ['confidentieel', 'Confidentieel'],
                        ['geheim', 'Geheim'],
                        ['zeer_geheim', 'Zeer geheim'],
                    ]}
                    value={this.state.max_va}
                    onChange={this.onVAChange}
                />
            </div>
        );
    }
}


InformatieobjecttypePermissionForm.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    initialData: PropTypes.arrayOf(PropTypes.object).isRequired,   // JSON object with keys {"catalogus": catalogus_url, "omschrijving_1": ["max_va_1", "id_1"], "omschrijving_2": ["max_va_2", "id_2"], ...}
    catalogData: PropTypes.arrayOf(PropTypes.array).isRequired, // Array of [cataog_url, catalog_label]
    informatieobjecttypeData: PropTypes.object.isRequired,                 // JSON object where the keys are the catalogs URLs and the values are lists of omschrijvingen
};

InformatieobjecttypeField.propTypes = {
    catalogus:  PropTypes.string.isRequired,
    checked:  PropTypes.string.isRequired,
    max_va:  PropTypes.string.isRequired,
    omschrijving:  PropTypes.string.isRequired,
    id:  PropTypes.number.isRequired,
};

export { InformatieobjecttypePermissionForm };
