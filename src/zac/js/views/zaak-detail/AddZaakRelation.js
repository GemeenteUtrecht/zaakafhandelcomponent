import React from 'react';
import Modal from 'react-modal';
import AsyncSelect from 'react-select/async';
import {HiddenInput} from '../../components/forms/Inputs';
import {ErrorList, SubmitRow, Wrapper} from '../../components/forms/Utils';
import {useImmerReducer} from 'use-immer';
import {apiCall, get} from '../../utils/fetch';
import {Select} from '../../components/forms/Select';
import {AARD_RELATIES} from '../../constants';
import {Label} from '../../components/forms/Label';
import {Help} from '../../components/forms/Help';

const ENDPOINT_ADD_RELATION = '/core/api/zaken_relation';
const ENDPOINT_ZAKEN = '/core/api/zaken';

const initialState = {
    errors: '',
    relationZaakIdentificatie: '',
    relationZaakUrl: '',
    aardRelatie: '',
    isModalOpen: false,

};


function reducer(draft, action) {
    switch (action.type) {
        case 'UPDATE_ZAAK_RELATION': {
            draft.relationZaakUrl = action.payload.value;
            break;
        }
        case 'UPDATE_AARD_RELATIE': {
            draft.aardRelatie = action.payload;
            break;
        }
        case 'VALIDATION_ERRORS': {
            draft.errors = action.payload;
            break;
        }
        case 'SET_MODAL_STATE': {
            draft.isModalOpen = action.payload;
            draft.errors = '';
            draft.relationZaakIdentificatie = '';
            draft.aardRelatie = '';
            break;
        }
        default:
            break;
    }
}


const getZaken = async (inputValue) => {
    const response = await get(ENDPOINT_ZAKEN, {identificatie: inputValue});
    return response.map( (zaak) => {
        return {
            value: zaak.url,
            label: `${zaak.identificatie} (${zaak.bronorganisatie})`,
        };
    } );
};


const AddZaakRelation = ({ zaakUrl, csrfToken, onSuccessfulSubmit }) => {
    const [state, dispatch] = useImmerReducer(reducer, initialState);
    const closeModal = () => {
        dispatch({type: 'SET_MODAL_STATE', payload: false});
    };

    const onSubmit = async (event) => {
        event.preventDefault();

        const data = new FormData();
        data.append('csrfmiddlewaretoken', csrfToken);
        data.append('main_zaak', zaakUrl);
        data.append('relation_zaak', state.relationZaakUrl);
        data.append('aard_relatie', state.aardRelatie);

        // post the form
        const response = await apiCall(
            ENDPOINT_ADD_RELATION,
            {
                method: 'POST',
                body: data
            }
        );

        if (response.ok) {
            dispatch({type: 'SET_MODAL_STATE', payload: false});
            onSuccessfulSubmit();
        } else if (response.status >= 500) {
            throw new Error('Server error.');
        } else if (response.status === 400) {
            const responseData = await response.json();
            dispatch({
                type: 'VALIDATION_ERRORS',
                payload: responseData,
            });
        }
    };

    const relationZaakErrors = state.errors.relationZaak ? state.errors.relationZaak : [];

    return (
        <React.Fragment>
            <div className='btn-row'>
                <a
                    href='#'
                    role='button'
                    className='btn btn--small'
                    onClick={ (e) => {
                        e.preventDefault();
                        dispatch({type: 'SET_MODAL_STATE', payload: true});
                    } }
                >
                <i className='material-icons'>add</i>
                Relatie toevoegen
                </a>
            </div>

            <Modal
              isOpen={ state.isModalOpen }
              className='modal'
              onRequestClose={closeModal}
            >
                <button onClick={ closeModal } className='modal__close btn'>&times;</button>
                <h1 className='page-title'>Relatie toevoegen</h1>
                <form onSubmit={ onSubmit }>
                    <HiddenInput id='id_main_zaak' name='main_zaak' value={zaakUrl}/>
                    <Wrapper errors={relationZaakErrors}>
                        <Label label='Identificatie' required={true} />
                        <Help helpText='Voeg de identificatie toe van de zaak die u wilt relateren.' />
                        <ErrorList errors={relationZaakErrors} />
                         <AsyncSelect
                            autoFocus
                            isClearable
                            cacheOptions
                            defaultOptions={false}
                            loadOptions={ getZaken }
                            onChange={ (value) => dispatch({
                                type: 'UPDATE_ZAAK_RELATION',
                                payload: value ? value : ''
                            }) }
                        />
                    </Wrapper>
                    <Select
                        name='aard_relatie'
                        id='id_aard_relatie'
                        label='Aard relatie'
                        required={true}
                        helpText='Aard van de relatie tussen de zaken.'
                        choices={[['', '------']].concat(AARD_RELATIES)}
                        value={state.aardRelatie}
                        onChange={(event) => dispatch({
                            type: 'UPDATE_AARD_RELATIE',
                            payload: event.target.value
                        })}
                        errors={state.errors.aardRelatie ? state.errors.aardRelatie : []}
                    />
                    <div className='modal__submitrow'>
                        <SubmitRow text='Toevoegen' />
                    </div>
                </form>
            </Modal>

        </React.Fragment>
    );
};

export {AddZaakRelation};
