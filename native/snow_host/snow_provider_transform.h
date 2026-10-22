/* Recovered local provider conversion; reference/ground_response_pose.py,
 * provider_pose_transform. XYZW, float32 operation order, no normalization.
 * This does not establish world/bone coordinate semantics. */
#ifndef SNOW_PROVIDER_TRANSFORM_H
#define SNOW_PROVIDER_TRANSFORM_H
#include <string.h>
static float snow_pf_add(float a,float b) { volatile float r=a+b; return r; }
static float snow_pf_mul(float a,float b) { volatile float r=a*b; return r; }
static float snow_pf_sub(float a,float b) { volatile float r=a-b; return r; }
static void snow_provider_transform(const float v[4],const float c[4],
        const float p[4],const float q[4],int direct,float position[4],float rotation[4]) {
    if (direct) { memcpy(position,v,16); memcpy(rotation,c,16); return; }
    float dot=snow_pf_add(snow_pf_mul(q[0],v[0]),snow_pf_add(snow_pf_mul(q[1],v[1]),snow_pf_mul(q[2],v[2])));
    float cross[4]={snow_pf_sub(snow_pf_mul(q[1],v[2]),snow_pf_mul(v[1],q[2])),
                    snow_pf_sub(snow_pf_mul(q[2],v[0]),snow_pf_mul(v[2],q[0])),
                    snow_pf_sub(snow_pf_mul(q[0],v[1]),snow_pf_mul(v[0],q[1])),0};
    float wterm=snow_pf_sub(snow_pf_mul(q[3],q[3]),.5f);
    for(int i=0;i<4;i++) position[i]=snow_pf_add(snow_pf_mul(snow_pf_add(
        snow_pf_add(snow_pf_mul(cross[i],q[3]),snow_pf_mul(dot,q[i])),
        snow_pf_mul(wterm,v[i])),i<3?2.f:0.f),p[i]);
    float coefficients[3][4]={{q[0],-q[0],q[0],-q[0]},
                              {q[1],q[1],-q[1],-q[1]},
                              {-q[2],q[2],q[2],-q[2]}};
    float values[3][4]={{c[3],c[2],c[1],c[0]},
                        {c[2],c[3],c[0],c[1]},
                        {c[1],c[0],c[3],c[2]}};
    for(int i=0;i<4;i++) rotation[i]=snow_pf_mul(q[3],c[i]);
    for(int j=0;j<3;j++) for(int i=0;i<4;i++)
        rotation[i]=snow_pf_add(snow_pf_mul(coefficients[j][i],values[j][i]),rotation[i]);
}
#endif
