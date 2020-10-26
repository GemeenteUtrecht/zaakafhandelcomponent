import React, {useState, useEffect} from 'react';
import PropTypes from 'prop-types';
import {Select} from '../forms/Select';
import {CheckboxInput, HiddenInput} from "../forms/Inputs";
import {get} from "../../utils/fetch";


const InformatieobjecttypeDelete = ({index, data}) => {

    const getMaxVADisplay = (max_va) => {
        const choices = {
            'openbaar': 'Openbaar',
            'beperkt_openbaar': 'Beperkt openbaar',
            'intern': 'Intern',
            'zaakvertrouwelijk': 'Zaakvertrouwelijk',
            'vertrouwelijk': 'Vertrouwelijk',
            'confidentieel': 'Confidentieel',
            'geheim': 'Geheim',
            'zeer_geheim': 'Zeer geheim',
        };

        return choices[max_va];
    };

    return (
        <div className="form__field-group">
            <HiddenInput name='omschrijving' id='id_omschrijving' value={ data.omschrijving } />
            <HiddenInput name='id' id='id_id' value={ data.id } />
            <HiddenInput name='catalogus' id='id_catalogus' value={ data.catalogus } />
            <HiddenInput name='DELETE' id='id_DELETE' value={ true } />
            <li key={"permission_to_delete" + index}>{data.omschrijving} ({getMaxVADisplay(data.max_va)})</li>
        </div>
    );
};


InformatieobjecttypeDelete.propTypes = {
    index: PropTypes.number,
    data: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        catalog: PropTypes.string,
        omschrijving: PropTypes.string,
        max_va: PropTypes.string,
        selected: PropTypes.string,
    }))
};

export { InformatieobjecttypeDelete };
