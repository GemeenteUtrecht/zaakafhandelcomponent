import React from 'react';
import PropTypes from 'prop-types';
import {FormSet} from './formset';
import {Select, FormSetSelect} from '../forms/Select';
import {CheckboxInput, HiddenInput} from "../forms/Inputs";



class InformatieobjecttypePermissionForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            selected: this.props.selected,
            max_va: this.props.max_va,
            catalogus: this.props.data.catalogus,
            omschrijving: this.props.data.omschrijving,
            id: this.props.data.id
        };

        this.onCheckChange = this.onCheckChange.bind(this);
        this.onVAChange = this.onVAChange.bind(this);
    }

    onCheckChange(event) {
        this.setState(state => ({selected: !state.selected}));
    }

    onVAChange(event) {
        this.setState({max_va: event.target.value});
    }

    render() {
        return (
            <div className="form__field-group">
                <HiddenInput name='omschrijving' id='id_omschrijving' value={ this.state.omschrijving } />
                <HiddenInput name='id' id='id_id' value={ this.state.id } />
                <HiddenInput name='catalogus' id='id_catalogus' value={ this.state.catalogus } />
                <CheckboxInput
                    name='selected'
                    id={'id_selected'}
                    checked={this.state.selected}
                    initial={this.state.selected}
                    value={this.state.selected}
                    onChange={this.onCheckChange}
                />
                <label>{this.state.omschrijving}</label>
                <FormSetSelect
                    name={'max_va'}
                    id={'id_max_va'}
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


class InformatieobjecttypeForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            currentCatalog: '',
            displayFormset: false,
            formData: [],
            emptyFormData: [],
            errors: "",
        };

        this.onCatalogChange = this.onCatalogChange.bind(this);
    }

    onCatalogChange(event) {
        this.setState({
            currentCatalog: event.target.value,
            displayFormset: event.target.value !== '',
        });

        // Fetch the informatieobjecttypen
        if (event.target.value !== '') {
            const apiURL = "/accounts/permission-sets/informatieobjecttypes?catalogus=" + event.target.value;
            window.fetch(apiURL).then(
                response => response.json()
            ).then(
                result => {
                    this.setState({formData:result.formData, emptyFormData: result.emptyFormData});
                },
                error => {
                    this.setState({errors: error});
                }
            );
        }
    }

    render() {
        return (
            <React.Fragment>
                 <Select
                    name='informatieobjecttype_catalogus'
                    id='id_informatieobjecttype_catalogus'
                    label='Catalogus'
                    helpText='Select the catalog containing the desired informatieobjecttype'
                    choices={this.props.catalogChoices}
                    value={this.state.currentCatalog}
                    onChange={this.onCatalogChange}
                />
                <FormSet
                    configuration={this.props.configuration}
                    renderForm={this.props.renderForm}
                    formData={this.state.formData}
                    emptyFormData={this.state.emptyFormData}
                />
            </React.Fragment>
        );
    }
}

InformatieobjecttypeForm.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        extra: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    renderForm: PropTypes.func.isRequired, // a render prop
    catalogChoices: PropTypes.arrayOf(PropTypes.array).isRequired,
};

export { InformatieobjecttypeForm, InformatieobjecttypePermissionForm };
