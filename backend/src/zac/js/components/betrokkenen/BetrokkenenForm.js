import React, { useContext } from 'react';
import PropTypes from 'prop-types';

import { useImmerReducer } from 'use-immer';
import { apiCall, post } from '../../utils/fetch';
import { TextArea } from '../forms/TextArea';
import { ErrorList, SubmitRow } from '../forms/Utils';
import Options from '../forms/Options';
import { CsrfTokenContext } from '../forms/context';

const betrokkeneFields = [
    {
        name: 'betrokkene',
        id: 'geboortedatum',
        value: 'geboorte.datum',
        label: 'Geboortedatum',
    },
    {
        name: 'betrokkene',
        id: 'geboorteland',
        value: 'geboorte.land',
        label: 'Geboorteland',
    },
    {
        name: 'betrokkene',
        id: 'naw',
        value: 'verblijfplaats',
        label: 'NAW',
    },
    {
        name: 'betrokkene',
        id: 'kinderen',
        value: 'kinderen',
        label: 'Kinderen',
    },
    {
        name: 'betrokkene',
        id: 'partners',
        value: 'partners',
        label: 'Partners',
    },
];

const initialState = {
    loading: false,
    hasError: false,
    fields: {
        value: [],
        errors: [],
    },
    doelbinding: {
        value: '',
        errors: [],
    },
};

function reducer(draft, action) {
    switch (action.type) {
    case 'DOELBINDING_CHANGED': {
        const { name, value } = action.payload;
        draft[name].value = value;
        draft[name].errors = [];
        break;
    }

    case 'BETROKKENE_PARAMS_CHANGED': {
        const { name, value, checked } = action.payload;
        if (checked) {
            if (!draft[name].value.includes(value)) {
                draft[name].value = [...draft[name].value, value];
            }
        } else {
            const index = draft[name].value.indexOf(value);
            if (index > -1) {
                draft[name].value.splice(index, 1);
            }
        }
        break;
    }

    case 'FETCH_STARTED': {
        draft.loading = true;
        break;
    }

    case 'FETCH_COMPLETED': {
        draft.loading = false;
        break;
    }

    case 'VALIDATION_ERRORS': {
        const errors = action.payload;
        draft.hasError = true;
        Object.entries(errors).map((field, error) => {
            draft[field].error = error;
        });
        break;
    }

    default:
        break;
    }
}

const postBetrokkeneData = async (endpoint, csrftoken, formData) => {
    // send the API call
    const response = await post(endpoint, csrftoken, formData);

    if (response.status >= 500) {
        throw new Error('Server error.');
    }

    return {
        ok: response.ok,
        status: response.status,
        data: response.data,
    };
};

const BetrokkenenForm = ({ bsn, onFetchBetrokkeneComplete }) => {
    const endpoint = '/core/api/betrokkene/info';
    const [state, dispatch] = useImmerReducer(reducer, initialState);
    const csrftoken = useContext(CsrfTokenContext);

    const handleChange = (event) => {
        const { name, value, checked } = event.target;
        if (name === 'doelbinding') {
            dispatch({
                type: 'DOELBINDING_CHANGED',
                payload: {
                    name,
                    value,
                },
            });
        } else if (name === 'betrokkene') {
            dispatch({
                type: 'BETROKKENE_PARAMS_CHANGED',
                payload: {
                    name: 'fields',
                    value,
                    checked,
                },
            });
        }
    };

    const onSubmit = async (event) => {
        const formData = {
            burgerservicenummer: bsn,
            doelbinding: state.doelbinding.value,
            fields: state.fields.value.join(),
        };
        event.preventDefault();

        dispatch({ type: 'FETCH_STARTED' });

        const fetchBetrokkeneResult = await postBetrokkeneData(endpoint, csrftoken, formData);

        dispatch({ type: 'FETCH_COMPLETED' });

        if (!fetchBetrokkeneResult.ok) {
            if (fetchBetrokkeneResult.status === 400) {
                dispatch({
                    type: 'VALIDATION_ERRORS',
                    payload: fetchBetrokkeneResult.data,
                });
            }
        } else {
            const betrokkeneData = fetchBetrokkeneResult.data;
            if (onFetchBetrokkeneComplete) {
                onFetchBetrokkeneComplete(betrokkeneData);
            }
        }
    };

    if (state.loading) {
        return (
            <div className="loader-wrapper">
                <span className="loader" />
            </div>
        );
    }

    if (state.hasError) {
        return (
            <>
                <ErrorList errors={state.fields.errors} />
                <ErrorList errors={state.doelbinding.errors} />
            </>
        );
    }

    return (
        <form onSubmit={onSubmit} className="form form--modal">
            <h2 className="page-title">Toon bijkomende gegevens:</h2>
            <ul className="checkbox-select" style={{ marginBottom: '2rem' }}>
                <Options
                    onChange={handleChange}
                    options={betrokkeneFields}
                    required
                />
            </ul>
            <TextArea
                id="id_doelbinding"
                name="doelbinding"
                label="Specificeer de doelbinding voor het opvragen van deze gegevens:"
                onChange={handleChange}
                value={state.doelbinding.value}
                errors={state.doelbinding.errors}
                required
            />
            <div className="modal__submitrow">
                <SubmitRow
                    text="Opvragen"
                    isDisabled={state.fields.value.length <= 0 || !state.doelbinding.value}
                />
            </div>
        </form>
    );
};

BetrokkenenForm.propTypes = {
    bsn: PropTypes.string.isRequired,
    onFetchBetrokkeneComplete: PropTypes.func.isRequired,
};

export default BetrokkenenForm;
