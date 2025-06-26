# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 CERN.
#
# CDS-RDM is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""ISNPIRE harvester transformer tests."""

from idutils.normalizers import normalize_isbn
from invenio_vocabularies.datastreams import StreamEntry

from cds_rdm.inspire_harvester.transformer import InspireJsonTransformer

transformer_entry1 = {
    "metadata": {
        "persistent_identifiers": [
            {"schema": "URN", "value": "urn:nbn:de:hebis:77-25439"},
            {"schema": "ARK", "value": "ark_value"},
        ],
        "corporate_author": ["Okamura, Shinichi", "Lou, Xuanhong"],
        "keywords": [
            {"value": "quantum mechanics", "schema": "INSPIRE"},
            {"value": "relativity theory", "schema": "INSPIRE"},
        ],
        "dois": [{"value": "10.17181/405kf-bmq61"}, {"value": "10.12345/354hh-bkd29"}],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "affiliations": [
                    {"value": "Rio de Janeiro State U."},
                    {"value": "CERN"},
                ],
                "last_name": "Torres da Silva de Araujo",
                "first_name": "F.",
                "inspire_roles": ["supervisor"],
            }
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
                "description": "PhD_thesis_Okamura",
                "original_url": "https://www.ifisica.uaslp.mx/~jurgen/AkbarEmmanuelDiazRodarte-Lic.pdf",
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [
            {"legacy_name": "ALICE"},
            {"legacy_name": "ATLAS"},
            {"accelerator": "CERN LEP"},
            {"accelerator": "CERN LHC"},
        ],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 5485717,
        "document_type": ["thesis"],
        "languages": ["pt", "es"],
        "abstracts": [
            {
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            },
            {
                "value": "It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            },
        ],
        "imprints": [
            {
                "date": "2021",
                "publisher": "Springer",
            }
        ],
        "titles": [
            {
                "title": "Estudo das correlações cinemáticas em topologias de difração dura no contexto do CMS/LHC",
            },
            {
                "title": "Modified big bang nucleosynthesis with nonstandard neutron sources",
            },
            {
                "title": "Particles, Strings and the Early Universe",
                "subtitle": "The Structure of Matter and Space-Time",
            },
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "date": "2010",
            "degree_type": "Master",
            "defense_date": "2010-03-12",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "5485717",
}

transformer_entry2 = {
    "metadata": {
        "persistent_identifiers": [
            {"schema": "HDL", "value": "10589/89683"},
            {"schema": "ARK", "value": "ark_value"},
        ],
        "copyright": [
            {
                "statement": "All rights reserved",
                "url": "https://example.com/license",
            }
        ],
        "figures": [
            {
                "key": "045edb54c43321ece5162968bee5d386",
                "url": "https://inspirehep.net/files/045edb54c43321ece5162968bee5d386",
                "filename": "Fulltext.pdf",
            }
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "last_name": "Torres da Silva de Araujo",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                    {
                        "schema": "INSPIRE BAI",
                        "value": "F.Torres.Da.Silva.De.Araujo.1",
                    },
                ],
                "first_name": "F.",
                "inspire_roles": ["supervisor"],
            }
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
            },
            {
                "key": "d9aa7bff4b8bf62626c043238ff41c0a",
                "url": "https://inspirehep.net/files/d9aa7bff4b8bf62626c043238ff41c0a",
                "filename": "CERN-THESIS-2020-183.pdf",
            },
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [{"legacy_name": "CERN-LHC-CMS"}],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 9885717,
        "document_type": ["thesis", "article"],
        "languages": ["blaaaa"],
        "titles": [
            {
                "title": "Estudo das correlações cinemáticas em topologias de difração dura no contexto do CMS/LHC",
            },
        ],
        "external_system_identifiers": [{"schema": "SPIRES", "value": "48848484"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
            "defense_date": "2010-03-12",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "9885717",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry3 = {
    "metadata": {
        "isbns": [{"value": "978-0-306-40615-7", "medium": "online"}],
        "dois": [
            {"value": "blaa"},
        ],
        "copyright": [
            {
                "holder": "Jane Doe",
                "year": "2020",
            }
        ],
        "imprints": [
            {
                "date": "2021",
                "publisher": "Springer",
            },
            {
                "date": "2021",
                "publisher": "CERN",
            },
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "affiliations": [
                    {"value": "Rio de Janeiro State U."},
                    {"value": "CERN"},
                ],
                "last_name": "Torres da Silva de Araujo",
                "first_name": "F.",
            }
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
            }
        ],
        "figures": [
            {
                "key": "045edb54c43321ece5162968bee5d386",
                "url": "https://inspirehep.net/files/045edb54c43321ece5162968bee5d386",
                "filename": "Fulltext.pdf",
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [
            {"legacy_name": "invalid"},
            {"accelerator": "invalid"},
        ],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 5585717,
        "document_type": ["thesis"],
        "abstracts": [
            {
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            }
        ],
        "external_system_identifiers": [{"schema": "blaaa", "value": "444ii3u4u3"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "5585717",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry4 = {
    "metadata": {
        "book_series": [
            {
                "title": "Harry Potter",
                "volume": "Vol. 2",
            }
        ],
        "dois": [{"value": "10.17181/405kf-bmq61"}],
        "copyright": [
            {
                "statement": "All rights reserved",
                "url": "https://example.com/license",
                "holder": "Jane Doe",
                "year": "2020",
            }
        ],
        "imprints": [
            {
                "date": "2021",
                "place": "Geneva",
            },
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "last_name": "Torres da Silva de Araujo",
                "first_name": "F.",
                "inspire_roles": ["author"],
            }
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [{"legacy_name": "CERN-LHC-CMS"}],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 8685717,
        "document_type": ["thesis"],
        "languages": ["pt"],
        "abstracts": [
            {
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            }
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633899"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "8685717",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry5 = {
    "metadata": {
        "book_series": [
            {
                "title": "Harry Potter",
            },
            {
                "title": "The Lord of the Rings",
            },
        ],
        "isbns": [
            {"value": "978-0-306-40615-7", "medium": "online"},
            {"value": "978-3-16-148410-0", "medium": "online"},
            {
                "value": "1234",
                "medium": "online",
            },
        ],
        "dois": [{"value": "10.12345/354hh-bkd29"}],
        "copyright": [
            {
                "statement": "All rights reserved",
                "url": "https://example.com/license",
                "year": "2020",
            }
        ],
        "imprints": [
            {
                "date": "invalid",
            },
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
            }
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Torres da Silva de Araujo",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                    {
                        "schema": "INSPIRE BAI",
                        "value": "F.Torres.Da.Silva.De.Araujo.1",
                    },
                ],
                "first_name": "F.",
                "inspire_roles": ["editor"],
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [{"legacy_name": "CERN-LHC-CMS"}],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 1685719,
        "document_type": ["thesis"],
        "languages": ["pt"],
        "abstracts": [
            {
                "source": "submitter",
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            }
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "1685719",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry6 = {
    "metadata": {
        "isbns": [
            {
                "value": "978-3-16-148410-0",
                "medium": "online",
            },
        ],
        "copyright": [
            {
                "statement": "All rights reserved",
                "url": "https://example.com/license",
                "year": "2020",
            },
            {
                "url": "https://example.com/license",
                "year": "2020",
            },
        ],
        "imprints": [
            {
                "date": "2023",
                "place": "Geneva",
            },
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Torres da Silva de Araujo",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                    {
                        "schema": "INSPIRE BAI",
                        "value": "F.Torres.Da.Silva.De.Araujo.1",
                    },
                ],
                "first_name": "F.",
            }
        ],
        "documents": [
            {
                "filename": "Thesis Torres da Silva de Araujo .pdf",
                "fulltext": True,
                "key": "4f2b64c86329058fb460ce7d9e806541",
                "url": "https://inspirehep.net/files/4f2b64c86329058fb460ce7d9e806541",
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [{"legacy_name": "CERN-LHC-CMS"}],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 2685719,
        "document_type": ["thesis"],
        "languages": ["pt"],
        "abstracts": [
            {
                "source": "submitter",
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            }
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "2685719",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry7 = {
    "metadata": {
        "isbns": [
            {
                "value": "978-3-16-148410-0",
                "medium": "online",
            },
        ],
        "copyright": [
            {
                "statement": "All rights reserved",
                "url": "https://example.com/license",
                "year": "2020",
            },
            {
                "url": "https://example.com/license",
                "year": "2020",
            },
        ],
        "imprints": [
            {
                "date": "2023",
                "place": "Geneva",
            },
        ],
        "authors": [
            {
                "full_name": "Torres da Silva de Araujo, F.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Torres da Silva de Araujo",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                    {
                        "schema": "INSPIRE BAI",
                        "value": "F.Torres.Da.Silva.De.Araujo.1",
                    },
                ],
                "first_name": "F.",
            }
        ],
        "number_of_pages": 115,
        "accelerator_experiments": [{"legacy_name": "CERN-LHC-CMS"}],
        "author_count": 1,
        "urls": [
            {
                "description": "UERJ server",
                "value": "http://www.bdtd.uerj.br/tde_busca/arquivo.php?codArquivo=3340",
            }
        ],
        "first_author": {
            "full_name": "Torres da Silva de Araujo, F.",
            "last_name": "Torres da Silva de Araujo",
            "ids": [
                {"schema": "INSPIRE ID", "value": "INSPIRE-00175930"},
                {"schema": "INSPIRE BAI", "value": "F.Torres.Da.Silva.De.Araujo.1"},
            ],
            "first_name": "F.",
        },
        "control_number": 2685000,
        "document_type": ["thesis"],
        "languages": ["pt"],
        "abstracts": [
            {
                "source": "submitter",
                "value": "This work is about the study, by means of a Monte Carlo simulation, of correlations in kinematical variables on topologies of single diffraction and double pomeron exchange looking for determinate and study the phase space of the cited topologies, specially in what is about inclusive production of dijets at CMS/LHC. It will be also presented an analysis on the single diffractive production of inclusive dijets at center of mass energy √s = 14 TeV (also bymeans of a Monte Carlo simulation), in which we established a data-driven procedure, for the observation of this kind of process. We also analyze the impact of different values of rapidity gap survival probability, [|S²|], on the results, in such a way that we can conclude that an observation of inclusive diffractive dijets, in 10 pb-1 of data, using the procedure proposed, may exclude very low values of [|S²|].",
            }
        ],
        "external_system_identifiers": [{"schema": "CDS", "value": "2633876"}],
        "thesis_info": {
            "institutions": [{"name": "Rio de Janeiro State U."}],
            "degree_type": "Master",
        },
        "supervisors": [
            {
                "full_name": "Franco de Sa Santoro, A.",
                "affiliations": [{"value": "Rio de Janeiro State U."}],
                "last_name": "Franco de Sa Santoro",
                "ids": [{"schema": "INSPIRE BAI", "value": "A.Franco.de.Sa.Santoro.2"}],
                "inspire_roles": ["supervisor"],
                "first_name": "A.",
            }
        ],
    },
    "id": "2685000",
    "created": "2020-01-01T00:00:00Z",
}

transformer_entry8 = {
    "metadata": {
        "titles": [{"title": "A new hope"}],
        "collaboration": [{"value": "CMS"}],
        "license": [
            {"imposing": "CERN", "license": "CC-BY-4.0", "url": "https://license"}
        ],
        "public_notes": [{"value": "Important note"}],
        "record_affiliations": [{"record": "CERN"}],
        "title_translations": [{"language": "fr", "title": "Un nouvel espoir"}],
        "related_records": [
            {"record": "https://cds.cern.ch/record/12345", "relation": "successor"}
        ],
        "publication_info": [
            {
                "journal_title": "Phys.Lett.B",
                "journal_volume": "42",
                "journal_issue": "1",
                "artid": "123",
                "page_start": "10",
                "page_end": "20",
                "cnum": "C23-07-12",
                "conf_acronym": "ICHEP",
                "conference_record": "https://inspirehep.net/conferences/54321",
                "parent_isbn": "978-0-306-40615-7",
                "parent_record": "https://cds.cern.ch/record/54321",
                "parent_report_number": "CERN-REP-2024-001",
                "journal_record": "https://cds.cern.ch/record/33333",
            }
        ],
        "control_number": 2685001,
        "thesis_info": {
            "date": "2021-05-01",
            "defense_date": "2022-01-01",
            "degree_type": "PhD",
            "institutions": [{"name": "CERN"}],
        },
        "authors": [{"first_name": "A", "last_name": "Author"}],
        "documents": [{"filename": "file.pdf", "key": "123", "url": "url"}],
    },
    "id": "2685001",
}

transformer_entry9 = {
    "metadata": {
        "titles": [{"title": "Missing fields"}],
        "authors": [{"first_name": "A", "last_name": "Author"}],
        "documents": [{"filename": "file.pdf", "key": "123", "url": "url"}],
        "related_records": [{"record": "123ABC", "relation": "other"}],
        "control_number": 2685002,
    },
    "id": "2685002",
}

transformer_entry10 = {
    "metadata": {
        "keywords": [
            {"value": "existing-cern-subject", "schema": "CERN"},
            {"value": "NonExisting CERN subject", "schema": "CERN"},
            {"value": "existing-cds-subject", "schema": "CDS"},
            {"value": "NonExisting CDS subject", "schema": "CDS"},
            {"value": "Skip PACS", "schema": "PACS"},
            {"value": "Skip CERN LIBRARY", "schema": "CERN LIBRARY"},
            {"value": "Other schema subject", "schema": "OTHER"},
        ],
        "authors": [],
        "documents": [{"filename": "file.pdf", "key": "key", "url": "url"}],
        "control_number": 2685003,
    },
    "id": "2685003",
}


def test_transformer(running_app, caplog):
    """Test transformation rules."""
    transformer = InspireJsonTransformer()

    result1 = transformer.apply(StreamEntry(transformer_entry1))
    result2 = transformer.apply(StreamEntry(transformer_entry2))
    result3 = transformer.apply(StreamEntry(transformer_entry3))
    result4 = transformer.apply(StreamEntry(transformer_entry4))
    result5 = transformer.apply(StreamEntry(transformer_entry5))
    result6 = transformer.apply(StreamEntry(transformer_entry6))
    result7 = transformer.apply(StreamEntry(transformer_entry7))
    result8 = transformer.apply(StreamEntry(transformer_entry8))
    result9 = transformer.apply(StreamEntry(transformer_entry9))
    result10 = transformer.apply(StreamEntry(transformer_entry10))

    record1 = result1.entry
    record2 = result2.entry
    record3 = result3.entry
    record4 = result4.entry
    record5 = result5.entry
    record6 = result6.entry
    record7 = result7.entry
    record8 = result8.entry
    record9 = result9.entry
    record10 = result10.entry

    # Assertions
    # ----- Titles -----
    # case 1: 2 titles, 1 subtitle
    assert (
        result1.entry["metadata"]["title"]
        == transformer_entry1["metadata"]["titles"][0]["title"]
    )
    assert {
        "title": transformer_entry1["metadata"]["titles"][1]["title"],
        "type": {"id": "alternative-title"},
    } in record1["metadata"]["additional_titles"]
    assert {
        "title": transformer_entry1["metadata"]["titles"][2]["title"],
        "type": {"id": "alternative-title"},
    } in record1["metadata"]["additional_titles"]
    assert {
        "title": transformer_entry1["metadata"]["titles"][2]["subtitle"],
        "type": {"id": "subtitle"},
    } in record1["metadata"]["additional_titles"]

    # case 2: only 1 title
    assert (
        record2["metadata"]["title"]
        == transformer_entry2["metadata"]["titles"][0]["title"]
    )
    assert "additional_titles" not in record2["metadata"]

    # case 3: 0 titles
    assert "title" not in record3["metadata"]
    assert "additional_titles" not in record3["metadata"]

    # ----- Publisher -----
    # case 1: publisher present
    assert (
        record1["metadata"]["publisher"]
        == transformer_entry1["metadata"]["imprints"][0]["publisher"]
    )

    # case 2: publisher absent
    assert "publisher" not in record2["metadata"]

    # case 3: more than 2 imprints found (error)
    assert "More than 1 imprint found. INSPIRE record id: 5585717." in result3.errors[0]
    assert "publisher" not in record3["metadata"]

    # ----- Publication date -----
    # case 1: coming from thesis_info.date
    assert (
        record1["metadata"]["publication_date"]
        == transformer_entry1["metadata"]["thesis_info"]["date"]
    )

    # case 2: nothing found for publication_date (error)
    assert "publication_date" not in record2["metadata"]
    assert (
        "Couldn't get publication date. INSPIRE record id: 9885717."
        in result2.errors[0]
    )
    # case 3: coming from imprint.date
    assert (
        record4["metadata"]["publication_date"]
        == transformer_entry4["metadata"]["imprints"][0]["date"]
    )

    # case 4: nothing found for publication_date (error)
    assert "publication_date" not in record3["metadata"]
    assert (
        "Couldn't get publication date. INSPIRE record id: 5585717."
        in result3.errors[0]
    )

    # case 5: parsing exception
    assert "publication_date" not in record5["metadata"]
    assert (
        "Error occurred while parsing imprint.date to EDTF level 0 format for publication_date. INSPIRE record id: 1685719. Date: invalid. Error: Error at position 0: Invalid input or format near 'invalid'. Please provide a valid EDTF string.."
        in result5.errors[0]
    )

    # ----- Document type -----
    # case 1: thesis
    assert record1["metadata"]["resource_type"] == {"id": "publication-thesis"}
    # case 2: articles (not supported - error)
    assert "resource_type" not in record2["metadata"]
    assert "Only thesis are supported for now." in result2.errors[0]

    # ----- Copyrights -----
    # case 1: all parts empty
    assert "copyright" not in record1["metadata"]

    # case 2: holder and year are empty
    assert (
        record2["metadata"]["copyright"]
        == "© All rights reserved https://example.com/license"
    )

    # case 3: statement and url are empty
    assert record3["metadata"]["copyright"] == "© Jane Doe 2020"

    # case 4: all parts present
    assert (
        record4["metadata"]["copyright"]
        == "© Jane Doe 2020, All rights reserved https://example.com/license"
    )

    # case 5: holder is empty
    assert (
        record5["metadata"]["copyright"]
        == "© 2020, All rights reserved https://example.com/license"
    )

    # case 5: 2 copyrights present
    assert (
        record6["metadata"]["copyright"]
        == "© 2020, All rights reserved https://example.com/license<br />© 2020, https://example.com/license"
    )

    # ----- DOIs -----
    # case 1: more than 1 found (error)
    assert "pids" not in record1["metadata"]
    assert (
        "More than 1 DOI was found in the INSPIRE record #5485717." in result1.errors[0]
    )

    # case 2: no dois found
    assert "pids" not in record2["metadata"]

    # case 3: invalid doi found (error)
    assert (
        "DOI validation failed. Value: blaa. INSPIRE record #5585717."
        in result3.errors[0]
    )
    assert "pids" not in record2["metadata"]

    # case 4: map CDS doi
    assert record4["pids"]["doi"] == {
        "identifier": "10.17181/405kf-bmq61",
        "provider": "datacite",
    }
    # case 5: map external doi
    assert record5["pids"]["doi"] == {
        "identifier": "10.12345/354hh-bkd29",
        "provider": "external",
    }

    # ----- Abstracts -----
    # case 1: abstract present
    assert (
        record1["metadata"]["description"]
        == transformer_entry1["metadata"]["abstracts"][0]["value"]
    )

    # case 2: abstract absent
    assert "description" not in record2["metadata"]

    # ----- Subjects -----
    # case 1: 2 keywords present
    assert record1["metadata"]["subjects"] == [
        {
            "subject": transformer_entry1["metadata"]["keywords"][0]["value"],
        },
        {
            "subject": transformer_entry1["metadata"]["keywords"][1]["value"],
        },
    ]

    # case 2: keywords absent
    assert "subjects" not in record2["metadata"]

    # case 3: keywords present with schema logic
    subjects = record10["metadata"]["subjects"]

    assert {"subject": "NonExisting CERN subject"} in subjects
    assert {"id": "existing-cern-subject"} in subjects
    assert {"subject": "NonExisting CDS subject"} in subjects
    assert {"id": "existing-cds-subject"} in subjects
    assert {"subject": "Other schema subject"} in subjects
    assert all(s.get("subject") != "Skip PACS" for s in subjects)
    assert all(s.get("subject") != "Skip CERN LIBRARY" for s in subjects)

    # ----- Languages -----
    # case 1: 2 languages mapped correctly
    assert record1["metadata"]["languages"] == [{"id": "por"}, {"id": "spa"}]

    # case 2: parsing error
    assert "languages" not in record2["metadata"]
    assert (
        "Error occurred while mapping language 'blaaaa'. INSPIRE record id: 9885717. Error: 'NoneType' object has no attribute 'alpha_3'."
        in result2.errors[0]
    )

    # case 3: no languages present
    assert "languages" not in record3["metadata"]

    # ----- Alternate identifiers -----
    # case 1: INSPIRE id
    assert {
        "identifier": str(transformer_entry1["metadata"]["control_number"]),
        "scheme": "inspire",
    } in record1["metadata"]["identifiers"]

    # case 2: external_system_identifiers schema to drop
    assert {
        "identifier": str(
            transformer_entry2["metadata"]["external_system_identifiers"][0]["value"]
        ),
        "scheme": transformer_entry2["metadata"]["external_system_identifiers"][0][
            "schema"
        ],
    } not in record2["metadata"]["identifiers"]

    # case 3: external_system_identifiers schema unknown (error)
    assert (
        "Unexpected schema found in external_system_identifiers. Schema: blaaa, value: 444ii3u4u3. INSPIRE record id: 5585717."
        in result3.errors[0]
    )

    # case 4: external_system_identifiers mapped successfully
    assert {
        "identifier": str(
            transformer_entry4["metadata"]["external_system_identifiers"][0]["value"]
        ),
        "scheme": "lcds",
    } in record4["metadata"]["identifiers"]

    # case 5: ISBN invalid (error)
    assert "Invalid ISBN '1234'." in result5.errors[0]

    # case 6: ISBN successfully mapped
    assert {
        "identifier": str(transformer_entry6["metadata"]["isbns"][0]["value"]),
        "scheme": "isbn",
    } in record6["metadata"]["identifiers"]

    # ----- Contributors -----
    # case 1: 2 corporate_authors
    assert {
        "person_or_org": {
            "type": "organizational",
            "name": transformer_entry1["metadata"]["corporate_author"][0],
        }
    } in record1["metadata"]["contributor"]

    assert {
        "person_or_org": {
            "type": "organizational",
            "name": transformer_entry1["metadata"]["corporate_author"][1],
        }
    } in record1["metadata"]["contributor"]

    # case 2: has 'supervisor' in inspire_roles
    # family_name, given_name, name, role, 2 affiliations successfully mapped
    assert record1["metadata"]["contributor"][0]["person_or_org"] == {
        "type": "personal",
        "family_name": "Torres da Silva de Araujo",
        "given_name": "F.",
        "name": "Torres da Silva de Araujo, F.",
    }

    assert record1["metadata"]["contributor"][0]["role"]["id"] == "supervisor"

    assert record1["metadata"]["contributor"][0]["affiliations"] == [
        {
            "name": transformer_entry1["metadata"]["authors"][0]["affiliations"][0][
                "value"
            ]
        },
        {
            "name": transformer_entry1["metadata"]["authors"][0]["affiliations"][1][
                "value"
            ]
        },
    ]

    # case 3: no affiliations, 1 identifier ignored, 1 identifier mapped
    assert "affiliations" not in record2["metadata"]["contributor"][0]
    assert (
        len(record2["metadata"]["contributor"][0]["person_or_org"]["identifiers"]) == 1
    )
    assert (
        record2["metadata"]["contributor"][0]["person_or_org"]["identifiers"][0][
            "identifier"
        ]
        == "INSPIRE-00175930"
    )
    assert (
        record2["metadata"]["contributor"][0]["person_or_org"]["identifiers"][0][
            "scheme"
        ]
        == "inspire_author"
    )

    # ----- Creators -----
    # case 1: inspire_roles is empty
    # family_name, given_name, name, 2 affiliations successfully mapped
    assert record3["metadata"]["creators"][0]["person_or_org"] == {
        "type": "personal",
        "family_name": "Torres da Silva de Araujo",
        "given_name": "F.",
        "name": "Torres da Silva de Araujo, F.",
    }

    assert "role" not in record3["metadata"]["creators"][0]

    assert record3["metadata"]["creators"][0]["affiliations"] == [
        {
            "name": transformer_entry1["metadata"]["authors"][0]["affiliations"][0][
                "value"
            ]
        },
        {
            "name": transformer_entry1["metadata"]["authors"][0]["affiliations"][1][
                "value"
            ]
        },
    ]

    # case 2: has 'author' in inspire_roles
    # no affiliations
    assert record4["metadata"]["creators"][0]["role"]["id"] == "author"
    assert "affiliations" not in record4["metadata"]["creators"][0]

    # case 3: has 'editor' in inspire_roles
    # 1 identifier ignored, 1 identifier mapped, role mapped
    assert record5["metadata"]["creators"][0]["role"]["id"] == "editor"
    assert len(record5["metadata"]["creators"][0]["person_or_org"]["identifiers"]) == 1
    assert (
        record5["metadata"]["creators"][0]["person_or_org"]["identifiers"][0][
            "identifier"
        ]
        == "INSPIRE-00175930"
    )
    assert (
        record5["metadata"]["creators"][0]["person_or_org"]["identifiers"][0]["scheme"]
        == "inspire_author"
    )

    # ----- Creators: full_name fallback -----
    transformer_entry_creators = {
        "metadata": {
            "authors": [
                {"full_name": "Doe, John", "inspire_roles": []},
                {"full_name": "Madonna", "inspire_roles": []},
                {
                    "first_name": "John",
                    "last_name": "Smith",
                    "full_name": "Smith, John",
                    "inspire_roles": [],
                    "ids": [
                        {"schema": "ORCID", "value": "0000-0002-1825-0097"},
                        {"schema": "INSPIRE ID", "value": "INSPIRE-00123456"},
                    ],
                },
            ],
            "documents": [{"filename": "file.pdf", "key": "key", "url": "url"}],
            "control_number": 9999998,
        },
        "id": "9999998",
    }

    result_creators = transformer.apply(StreamEntry(transformer_entry_creators))
    record_creators = result_creators.entry
    creators = record_creators["metadata"]["creators"]

    # case 4: full_name present, first_name and last_name missing
    assert creators[0]["person_or_org"]["given_name"] == "John"
    assert creators[0]["person_or_org"]["family_name"] == "Doe"
    assert creators[0]["person_or_org"]["name"] == "Doe, John"

    # case 5: full_name present without comma, fallback to family_name only
    assert creators[1]["person_or_org"]["family_name"] == "Madonna"
    assert "given_name" not in creators[1]["person_or_org"]
    assert "name" not in creators[1]["person_or_org"]

    # case 6: author with ORCID identifier
    assert creators[2]["person_or_org"]["given_name"] == "John"
    assert creators[2]["person_or_org"]["family_name"] == "Smith"
    assert creators[2]["person_or_org"]["name"] == "Smith, John"

    identifiers = creators[2]["person_or_org"]["identifiers"]
    assert {"identifier": "0000-0002-1825-0097", "scheme": "orcid"} in identifiers
    assert {"identifier": "INSPIRE-00123456", "scheme": "inspire_author"} in identifiers

    # ----- Additional descriptions -----
    # case 1: 2 abstracts
    assert {
        "description": transformer_entry1["metadata"]["abstracts"][1]["value"],
        "type": {"id": "abstract"},
    } in record1["metadata"]["additional_descriptions"]

    # case 2: no descriptions
    assert "additional_descriptions" not in record3["metadata"]

    # case 3: book_title and book_volume
    assert {
        "description": transformer_entry4["metadata"]["book_series"][0]["title"],
        "type": {"id": "series-information"},
    } in record4["metadata"]["additional_descriptions"]

    assert {
        "description": transformer_entry4["metadata"]["book_series"][0]["volume"],
        "type": {"id": "series-information"},
    } in record4["metadata"]["additional_descriptions"]
    # case 4: 2 book_title
    assert {
        "description": transformer_entry5["metadata"]["book_series"][0]["title"],
        "type": {"id": "series-information"},
    } in record5["metadata"]["additional_descriptions"]
    assert {
        "description": transformer_entry5["metadata"]["book_series"][1]["title"],
        "type": {"id": "series-information"},
    } in record5["metadata"]["additional_descriptions"]

    # ----- Custom fields -----
    # case 1: imprint:imprint place
    assert {"place": transformer_entry4["metadata"]["imprints"][0]["place"]} == record4[
        "custom_fields"
    ]["imprint:imprint"]

    # case 2: imprint - ISBN with medium "online" and place
    assert {
        "place": transformer_entry6["metadata"]["imprints"][0]["place"],
        "isbn": transformer_entry6["metadata"]["isbns"][0]["value"],
    } == record6["custom_fields"]["imprint:imprint"]

    # case 3: imprint - 2 ISBNs with medium "online" (error)
    assert (
        "More than one electronic ISBN found: ['978-0-306-40615-7', '978-3-16-148410-0']."
        in result5.errors[0]
    )

    # case 4: 2 cern:accelerators
    assert {
        "id": transformer_entry1["metadata"]["accelerator_experiments"][2][
            "accelerator"
        ]
    } in record1["custom_fields"]["cern:accelerators"]
    assert {
        "id": transformer_entry1["metadata"]["accelerator_experiments"][3][
            "accelerator"
        ]
    } in record1["custom_fields"]["cern:accelerators"]

    # case 5: 2 cern:experiments
    assert {
        "id": transformer_entry1["metadata"]["accelerator_experiments"][0][
            "legacy_name"
        ]
    } in record1["custom_fields"]["cern:experiments"]
    assert {
        "id": transformer_entry1["metadata"]["accelerator_experiments"][1][
            "legacy_name"
        ]
    } in record1["custom_fields"]["cern:experiments"]

    # case 6: accelerator not found
    # assert "cern:accelerators" not in record3["custom_fields"]
    # assert (
    #     "Couldn't map accelerator 'invalid' value to anything in existing vocabulary. INSPIRE record id: 5585717."
    #     in caplog.text
    # )

    # # case 7: experiment not found
    # assert "cern:experiments" not in record3["custom_fields"]
    # assert (
    #     "Couldn't map experiment 'invalid' value to anything in existing vocabulary. INSPIRE record id: 5585717."
    #     in caplog.text
    # )

    # ----- Files -----
    # case 1: figures ignored
    assert "Fulltext.pdf" not in record3["files"]["entries"]

    # case 2: checksum, key, inspire_url mapped
    assert (
        record1["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"]["checksum"]
        == "md5:" + transformer_entry1["metadata"]["documents"][0]["key"]
    )
    assert (
        record1["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"]["key"]
        == transformer_entry1["metadata"]["documents"][0]["filename"]
    )
    assert (
        record1["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"][
            "inspire_url"
        ]
        == transformer_entry1["metadata"]["documents"][0]["url"]
    )

    # case 3: file metadata description and original_url
    assert (
        record1["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"][
            "metadata"
        ]["description"]
        == transformer_entry1["metadata"]["documents"][0]["description"]
    )
    assert (
        record1["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"][
            "metadata"
        ]["original_url"]
        == transformer_entry1["metadata"]["documents"][0]["original_url"]
    )

    # case 4: no files present error
    assert (
        "INSPIRE record #2685000 has no files. Metadata-only records are not supported. Aborting record transformation."
        in result7.errors[0]
    )
    assert record7 == None

    # case 5: 2 files
    assert (
        record2["files"]["entries"]["Thesis Torres da Silva de Araujo .pdf"]["checksum"]
        == "md5:" + transformer_entry2["metadata"]["documents"][0]["key"]
    )
    assert (
        record2["files"]["entries"]["CERN-THESIS-2020-183.pdf"]["checksum"]
        == "md5:" + transformer_entry2["metadata"]["documents"][1]["key"]
    )

    # ----- Persistent identifiers -----
    # case 1: 2 valid ids
    assert {
        "identifier": str(
            transformer_entry1["metadata"]["persistent_identifiers"][0]["value"]
        ),
        "scheme": "urn",
    } in record1["metadata"]["identifiers"]

    assert {
        "identifier": str(
            transformer_entry1["metadata"]["persistent_identifiers"][1]["value"]
        ),
        "scheme": "ark",
    } in record1["metadata"]["identifiers"]

    # case 2: 1 valid id, 1 invalid
    assert {
        "identifier": str(
            transformer_entry1["metadata"]["persistent_identifiers"][1]["value"]
        ),
        "scheme": "ark",
    } in record1["metadata"]["identifiers"]
    assert {
        "identifier": str(
            transformer_entry1["metadata"]["persistent_identifiers"][0]["value"]
        ),
        "scheme": "hdl",
    } not in record1["metadata"]["identifiers"]

    # case 3: urls added as identifiers
    assert {
        "identifier": transformer_entry1["metadata"]["urls"][0]["value"],
        "scheme": "url",
    } in record1["metadata"]["identifiers"]

    # ----- Collaborations -----
    assert {"person_or_org": {"type": "organizational", "name": "CMS"}} in record8[
        "metadata"
    ]["contributor"]
    assert {"person_or_org": {"type": "organizational", "name": "CERN"}} in record8[
        "metadata"
    ]["contributor"]
    assert "contributor" not in record9["metadata"]

    # ----- Rights -----
    transformer_entry_rights = {
        "metadata": {
            "license": [
                {"imposing": "CERN", "license": "CC-BY-4.0", "url": "https://license"}
            ],
            "documents": [{"filename": "file.pdf", "key": "key", "url": "url"}],
            "control_number": 9999999,
        },
        "id": "9999999",
    }

    transformer = InspireJsonTransformer()

    result_rights = transformer.apply(StreamEntry(transformer_entry_rights))
    record_rights = result_rights.entry
    rights = record_rights["metadata"]["rights"]
    print(rights)
    # case 1: license found in vocabulary
    assert rights[0]["description"] == "CERN"
    assert rights[0]["id"] == "cc-by-4.0"
    assert rights[0]["link"] == "https://license"

    # case 2: license not found in vocabulary
    transformer_entry_rights_missing = {
        "metadata": {
            "license": [
                {
                    "imposing": "CERN",
                    "license": "UNKNOWN-LICENSE",
                    "url": "https://license",
                }
            ],
            "documents": [{"filename": "file.pdf", "key": "key", "url": "url"}],
            "control_number": 9999999,
        },
        "id": "9999999",
    }

    result_rights_missing = transformer.apply(
        StreamEntry(transformer_entry_rights_missing)
    )
    record_rights_missing = result_rights_missing.entry
    rights_missing = record_rights_missing["metadata"]["rights"]

    assert rights_missing[0]["description"] == "CERN"
    assert rights_missing[0]["title"] == {"en": "UNKNOWN-LICENSE"}
    assert rights_missing[0]["link"] == "https://license"

    # ----- Public notes -----
    assert {
        "description": "Important note",
        "type": {"id": "other"},
    } in record8[
        "metadata"
    ]["additional_descriptions"]

    # ----- Title translations -----
    assert {
        "title": "Un nouvel espoir",
        "lang": "fr",
        "type": {"id": "translated-title"},
    } in record8["metadata"]["additional_titles"]

    # ----- Related identifiers -----
    assert {
        "identifier": "https://cds.cern.ch/record/12345",
        "scheme": "url",
        "relation_type": {"id": "is continued by"},
    } in record8["metadata"]["related_identifiers"]
    assert {
        "identifier": "https://cds.cern.ch/record/33333",
        "scheme": "url",
        "relation_type": {"id": "published_in"},
    } in record8["metadata"]["related_identifiers"]
    assert {
        "identifier": normalize_isbn("978-0-306-40615-7"),
        "scheme": "isbn",
        "relation_type": {"id": "published_in"},
    } in record8["metadata"]["related_identifiers"]

    # ----- Custom fields journal -----
    assert record8["custom_fields"]["journal:journal"]["title"] == "Phys.Lett.B"
    assert record8["custom_fields"]["journal:journal"]["volume"] == "42"
    assert record8["custom_fields"]["journal:journal"]["issue"] == "1"
    assert record8["custom_fields"]["journal:journal"]["page_range"] == "10-20"
    assert record8["custom_fields"]["journal:journal"]["pages"] == "10-20, 123"

    # ----- Custom fields meeting -----
    assert record8["custom_fields"]["meeting:meeting"]["acronym"] == "ICHEP"
    assert {
        "scheme": "inspire",
        "value": "C23-07-12",
    } in record8["custom_fields"][
        "meeting:meeting"
    ]["identifiers"]
    assert {
        "scheme": "url",
        "value": "https://inspirehep.net/conferences/54321",
    } in record8["custom_fields"]["meeting:meeting"]["identifiers"]

    # ----- Custom fields thesis -----
    assert record8["custom_fields"]["thesis:thesis"]["date_submitted"] == "2021-05-01"
    assert record8["custom_fields"]["thesis:thesis"]["date_defended"] == "2022-01-01"
    assert record8["custom_fields"]["thesis:thesis"]["type"] == "PhD"
    assert record8["custom_fields"]["thesis:thesis"]["university"] == "CERN"

    # ----- Related identifier errors -----
    assert "Unknown relation type 'other' for identifier '123ABC'." in result9.errors[0]
