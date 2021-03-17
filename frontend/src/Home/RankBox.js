import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image, Container, Menu, Grid, Form, Segment, Icon  } from 'semantic-ui-react'

import unrank from '../image/unrank.png';
import iron from '../image/Emblem_Iron.png';
import bronze from '../image/Emblem_Bronze.png';
import silver from '../image/Emblem_Silver.png';
import gold from '../image/Emblem_Gold.png';
import platinum from '../image/Emblem_Platinum.png';
import diamond from '../image/Emblem_Diamond.png';
import master from '../image/Emblem_Master.png';
import grandmaster from '../image/Emblem_Grandmaster.png';
import challenger from '../image/Emblem_Challenger.png';

import './RankBox.css';


const rankTo=(rank)=>{
    let r = String(rank);
    if(r.length==1){
        return 'IRON ' + r
    }
    if(r[0]==1){
        return 'BRONZE ' + r[1]
    }
    if(r[0]==2){
        return 'SILVER ' + r[1]
    }
    if(r[0]==3){
        return 'GOLD ' + r[1]
    }
    if(r[0]==4){
        return 'PLATINUM ' + r[1]
    }
    if(r[0]==5){
        return 'DIAMOND ' + r[1]
    }
    if(r[0]==6){
        return 'MASTER '
    }
    if(r[0]==7){
        return 'GRANDMASTER '
    }
    if(r[0]==8){
        return 'CHALLENGER '
    }
    return 'UNKNOWN'
}

const rankimg=(rank)=>{
    if(rank=='UNRANK')
        return unrank
    if(rank.includes('BRONZE'))
        return bronze
    if(rank.includes('SILVER'))
        return silver
    if(rank.includes('GOLD'))
        return gold
    if(rank.includes('PLATINUM'))
        return platinum
    if(rank.includes('DIAMOND'))
        return diamond
    if(rank.includes('MASTER'))
        return master
    if(rank.includes('GRANDMASTER'))
        return grandmaster
    if(rank.includes('CHALLENGER'))
        return challenger

    return unrank

}

const RankBox=(props)=>{
    const [wins, set_win] = useState('');
    const [losses, set_loss] = useState('');
    const [rank, set_rank] = useState('')



    useEffect(()=>{
        if(props.rankinfo['rank'] != 0){
            set_rank(rankTo(props.rankinfo['rank']))
            set_win(String(props.rankinfo['wins'])+'승 ')
            set_loss(String(props.rankinfo['losses'])+'패')
        }
        else{
            set_rank('UNRANK')
        }
    })

    if (props.mobile){
        return(
            <div className={props.className}>
           
            <span>
                <img src={rankimg(rank)} style={{height:'5rem'}}/>
            </span>
            <span className='rankbox_info_mobile'>

                <div>
                {props.isSolo? '솔랭':'자랭'}  
                </div>
                <div>
                {rank}
                </div>
                <div>
                {wins} {losses}
                </div>
            </span>
            
            </div>
        )
    }
    return(
        <div className='rankbox'>
           
            <span>
                <img src={rankimg(rank)} style={{height:'100px'}}/>
            </span>
            <span className='rankbox_info'>

                <div>
                {props.isSolo? '솔랭':'자랭'} 
                </div>
                <div>
                {rank}
                </div>
                <div>
                {wins} {losses}
                </div>
            </span>
            
        </div>
    )
}

export default RankBox;